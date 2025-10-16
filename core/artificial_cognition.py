# core/artificial_cognition.py
"""
Ailys' central "mind".
- One place to talk to language models (hosted or local).
- Every call is approval-gated via core.approval_queue.
- Returns raw, unmodified output (no stripping or auto-JSON).
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

# persistence & memory
from pathlib import Path
from datetime import datetime
import uuid
from memory.memory import save_memory_event

# Always import the module so we share the SAME singleton queue with GUI
import core.approval_queue as approvals

# ------------------------------ Configuration ------------------------------

# We support two provider modes out of the box:
#   provider=openai            → Official OpenAI API (model like "gpt-5" / "gpt-4o")
#   provider=openai_compatible → Local or third-party server exposing the OpenAI schema
#
# Config precedence:
#  1) Environment variables (easy to drive from your Config tab / .env)
#  2) Optional JSON file at config/llm.json (handy for presets)
#
# Environment variables we read if present:
#   AILYS_PROVIDER         ("openai" | "openai_compatible")
#   AILYS_MODEL            (e.g., "gpt-5", "gpt-4o", "llama-3.1-8b-instruct-q6")
#   AILYS_BASE_URL         (e.g., "http://localhost:11434/v1" for Ollama / LM Studio)
#   OPENAI_API_KEY         (only required for hosted OpenAI or compatible servers that need a key)
#   AILYS_DEFAULT_TEMPERATURE (optional float; default 0.3)
#   AILYS_DEFAULT_MAX_TOKENS  (optional int; provider/model dependent)

_CONFIG_FILE = os.path.join("config", "llm.json")

def _load_config_file() -> Dict[str, Any]:
    try:
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _cfg(key: str, default: Optional[str] = None) -> Optional[str]:
    file_cfg = _load_config_file()
    if key in os.environ and os.environ[key]:
        return os.environ[key]
    if key in file_cfg and file_cfg[key]:
        return str(file_cfg[key])
    return default

def _provider() -> str:
    return (_cfg("AILYS_PROVIDER", "openai") or "openai").strip().lower()

def _model() -> str:
    return (_cfg("AILYS_MODEL", "gpt-4o") or "gpt-4o").strip()

def _base_url() -> Optional[str]:
    val = _cfg("AILYS_BASE_URL", None)
    return val.strip() if isinstance(val, str) and val.strip() else None

def _api_key() -> Optional[str]:
    val = _cfg("OPENAI_API_KEY", None)
    return val.strip() if isinstance(val, str) and val.strip() else None

def _default_temperature() -> float:
    try:
        return float(_cfg("AILYS_DEFAULT_TEMPERATURE", "0.3"))
    except Exception:
        return 0.3

def _default_max_tokens() -> Optional[int]:
    v = _cfg("AILYS_DEFAULT_MAX_TOKENS", "")
    try:
        return int(v) if str(v).strip() else None
    except Exception:
        return None

# ------------------------------ Result object ------------------------------

@dataclass
class CognitionResult:
    model_id: str
    raw_text: str
    usage: Optional[Dict[str, Any]] = None   # tokens, cost, etc. if available
    provider: str = ""

# --- Persistence helpers (full-fidelity exchange logs) ----------------------

def _exchanges_dir() -> Path:
    """Directory where full exchange JSON records are persisted."""
    p = Path("memory") / "exchanges"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _persist_exchange(record: Dict[str, Any]) -> str:
    """
    Write the full exchange record as JSON and return the absolute path.
    """
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    sid = uuid.uuid4().hex[:8]
    path = _exchanges_dir() / f"{ts}_{sid}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return str(path.resolve())

# ------------------------------ Public API ---------------------------------

def ask(
    *,
    messages: Optional[List[Dict[str, str]]] = None,
    prompt: Optional[str] = None,
    description: str = "Artificial cognition request",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,   # approval wait; None = wait forever
) -> CognitionResult:
    """
    The ONLY function tasks should call.
    - Accepts either 'messages' (chat format) or a single 'prompt' (we wrap as user message).
    - Routes to the configured provider/model.
    - ALWAYS goes through the approval queue before touching network/secrets.
    - Returns raw, unmodified model text.
    """
    if not messages and not prompt:
        raise ValueError("ask(...): provide either 'messages' or 'prompt'.")

    # Normalize to messages
    if messages is None:
        messages = [{"role": "user", "content": str(prompt)}]

    prov = _provider()
    mdl = _model()
    base_url = _base_url()
    api_key = _api_key()
    temp = _default_temperature() if temperature is None else float(temperature)
    mx = _default_max_tokens() if max_tokens is None else int(max_tokens)

    def _do_call() -> CognitionResult:
        # We only import and read keys *inside* the call to respect approval gating.
        # Provider: OpenAI (official) or OpenAI-compatible (local server).
        try:
            from openai import OpenAI
        except Exception as e:
            # Keep the behavior consistent: surface as RuntimeError to caller thread
            raise RuntimeError(f"OpenAI SDK not available: {e}")

        # Build client safely
        kwargs = {}
        if prov == "openai_compatible":
            # Local servers often require base_url; some don't need an API key.
            if base_url:
                kwargs["base_url"] = base_url
            # Pass key if present; some local servers accept empty/no key.
            if api_key:
                kwargs["api_key"] = api_key
        else:
            # Hosted OpenAI requires API key
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set. Add it in the Config tab.")
            kwargs["api_key"] = api_key

        # Optional client-level timeout for safety
        if "timeout" not in kwargs:
            kwargs["timeout"] = 60

        client = OpenAI(**kwargs)

        # Build chat args
        chat_args: Dict[str, Any] = {
            "model": mdl,
            "messages": messages,
            "temperature": temp,
        }
        if mx is not None:
            chat_args["max_tokens"] = mx

        # Execute
        resp = client.chat.completions.create(**chat_args)
        content = resp.choices[0].message.content or ""
        usage = {}
        try:
            usage = {
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                "total_tokens": getattr(resp.usage, "total_tokens", None),
            }
        except Exception:
            usage = None

            # Persist exchange (best-effort full object + raw text)
            # Try to capture a serializable version of the response object.
            try:
                # OpenAI SDK v1 objects usually support model_dump()
                resp_dump = resp.model_dump()  # type: ignore[attr-defined]
            except Exception:
                try:
                    # Some SDKs expose .to_dict()
                    resp_dump = resp.to_dict()  # type: ignore[attr-defined]
                except Exception:
                    # Fallback string—still useful as a forensic breadcrumb
                    resp_dump = str(resp)

            exchange_record: Dict[str, Any] = {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "description": description,  # captured from outer scope
                "provider": prov,
                "model": mdl,
                "base_url": _base_url(),
                "parameters": {"temperature": temp, "max_tokens": mx},
                "messages": messages,  # exact input we sent
                "response": resp_dump,  # best-effort full object
                "raw_text": content,  # exact content as returned
                "usage": usage,
            }
            exchange_path = _persist_exchange(exchange_record)

            # Also drop a crystallized breadcrumb for later recall/analytics
            try:
                # Keep this tiny; no extra cognition here.
                snippet = (content if isinstance(content, str) else str(content))[:3000]
                save_memory_event(
                    event_type="cognition_exchange",
                    source_text=snippet,
                    ai_insight=f"Exchange stored at {exchange_path}.",
                    user_input=description,
                    tags=[f"provider:{prov}", f"model:{mdl}", "cognition", "llm"],
                    file_path=exchange_path,
                )
            except Exception:
                # Never block the main flow on memory I/O
                pass

            # Return raw text (no strip/trim) to avoid any downstream surprises
            return CognitionResult(
                model_id=mdl,
                raw_text=content if isinstance(content, str) else str(content),
                usage=usage,
                provider=prov
            )


        # Return raw text (no strip/trim) to avoid any downstream surprises
        return CognitionResult(
            model_id=mdl,
            raw_text=content if isinstance(content, str) else str(content),
            usage=usage,
            provider=prov
        )

    # Approval gate: only now will the call happen
    result = approvals.request_approval(
        description=f"{description} | provider={prov} model={mdl}",
        call_fn=_do_call,
        timeout=timeout
    )
    if not result:
        # Either denied, dryrun, or failure inside approval worker
        raise RuntimeError("Approval declined or failed; no result returned.")

    if not isinstance(result, CognitionResult):
        # Safety: if some unexpected value seeped through
        raise RuntimeError(f"Artificial cognition returned unexpected type: {type(result)!r}")

    return result


# ------------------------------ Convenience --------------------------------

def model_summary() -> str:
    """Small helper for GUI: shows current brain selection."""
    prov, mdl, burl = _provider(), _model(), _base_url() or ""
    if prov == "openai_compatible" and burl:
        return f"{mdl} @ {burl}"
    return mdl
