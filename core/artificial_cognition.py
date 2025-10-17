# core/artificial_cognition.py
"""
Ailys' central "mind".
- One place to talk to language models (hosted or local).
- Every call is approval-gated via core.approval_queue.
- Returns raw, unmodified output (no stripping or auto-JSON).
"""

from __future__ import annotations
import json
import traceback
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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

def _llm_timeout() -> float:
    try:
        return float(_cfg("AILYS_LLM_TIMEOUT", "60"))
    except Exception:
        return 60.0

def _provider() -> str:
    return (_cfg("AILYS_PROVIDER", "openai") or "openai").strip().lower()

def _model() -> str:
    return (_cfg("AILYS_MODEL", "gpt-5") or "gpt-5").strip()

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
    # Default to 2000 if user hasn't set anything.
    v = _cfg("AILYS_DEFAULT_MAX_TOKENS", "2000")
    try:
        return int(v) if str(v).strip() else 2000
    except Exception:
        return 2000


# ------------------------------ Result object ------------------------------

@dataclass
class CognitionResult:
    model_id: str
    raw_text: str
    usage: Optional[Dict[str, Any]] = None   # tokens, cost, etc. if available
    provider: str = ""

# --- Persistence helpers (full-fidelity exchange logs) ----------------------

def _resolve_exchanges_base() -> Path:
    """
    Resolve the base folder for cognition exchange logs.
    Priority:
      1) AILYS_EXCHANGES_DIR env var (absolute or relative to CWD)
      2) <repo_root>/memory/exchanges  (repo_root = two levels above this file)
    """
    env_dir = os.getenv("AILYS_EXCHANGES_DIR", "").strip()
    if env_dir:
        base = Path(env_dir).expanduser()
        if not base.is_absolute():
            base = Path.cwd() / base
        return base

    # default: <repo_root>/memory/exchanges
    # this file: core/artificial_cognition.py  → repo_root = parent.parent
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "memory" / "exchanges"

def _exchanges_dir() -> Path:
    p = _resolve_exchanges_base()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[cognition:PERSIST] ERROR creating exchanges dir {p}: {e}")
        print(traceback.format_exc())
    print(f"[cognition:PERSIST] exchanges_dir = {p}  (cwd={Path.cwd()})")
    return p

def _persist_snapshot(call_id: str, suffix: str, payload: Dict[str, Any]) -> str:
    """
    Write a small JSON snapshot for a stage in the lifecycle (queued, preflight, denied, etc.).
    File name: <utc>_<callid>_<suffix>.json
    Always best-effort; never throws.
    """
    try:
        base = _exchanges_dir()
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        path = base / f"{ts}_{call_id}_{suffix}.json"
        base.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                pass
        print(f"[cognition:PERSIST] snapshot '{suffix}' → {path}")
        return str(path.resolve())
    except Exception as e:
        print(f"[cognition:PERSIST] snapshot ERROR ({suffix}): {e}")
        return ""


def _persist_exchange(record: Dict[str, Any]) -> str:
    """
    Write the full exchange record as JSON and return the absolute path.
    """
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    sid = uuid.uuid4().hex[:8]
    path = _exchanges_dir() / f"{ts}_{sid}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        print(f"[cognition:PERSIST] wrote exchange JSON → {path}")
    except Exception as e:
        print(f"[cognition:PERSIST] ERROR writing {path}: {e}")
        print(traceback.format_exc())
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

    # right after we normalize `messages`
    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            raise ValueError(f"messages[{i}] is not a dict: {type(m).__name__}")
        if not isinstance(m.get("role"), str):
            raise ValueError(f"messages[{i}].role must be a string, got: {m.get('role')!r}")
        if "content" not in m:
            raise ValueError(f"messages[{i}] missing 'content'")

    prov = _provider()
    mdl = _model()
    base_url = _base_url()
    api_key = _api_key()
    temp = _default_temperature() if temperature is None else float(temperature)
    mx = _default_max_tokens() if max_tokens is None else int(max_tokens)

    call_id = uuid.uuid4().hex[:8]

    # Stage 1: awaiting approval snapshot
    _persist_snapshot(call_id, "queued", {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "description": description,
        "provider": prov,
        "model": mdl,
        "base_url": _base_url(),
        "parameters": {"temperature": temperature, "max_tokens": max_tokens},
        "messages_count": len(messages or []),
        "status": "awaiting_approval",
    })

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
            kwargs["timeout"] = _llm_timeout()

        # Disable SDK-level automatic retries: one approval = one HTTP call.
        kwargs["max_retries"] = 0
        client = OpenAI(**kwargs)

        # Build chat args
        chat_args: Dict[str, Any] = {
            "model": mdl,
            "messages": messages,
            "temperature": temp,
        }
        if mx is not None:
            chat_args["max_tokens"] = mx

        # Some providers/models (e.g., "gpt-5") reject non-default temperature.
        if prov == "openai" and mdl.lower().startswith("gpt-5") and "temperature" in chat_args:
            if temp is not None and float(temp) != 1.0:
                print("[cognition:CALL] dropping temperature for gpt-5 compatibility")
                chat_args.pop("temperature", None)


        # Execute (always run, even if max_tokens is None)
        print(f"[cognition:CALL] provider={prov} model={mdl} base_url={_base_url() or ''}")
        print(f"[cognition:CALL] cwd={Path.cwd()}  exchanges_base={_resolve_exchanges_base()}")
        print(f"[cognition:CALL] messages={len(messages)} temp={temp} max_tokens={mx}")

        print(f"[cognition:CALL] id={call_id} provider={prov} model={mdl} base_url={_base_url() or ''}")
        print(f"[cognition:CALL] id={call_id} cwd={Path.cwd()}  exchanges_base={_resolve_exchanges_base()}")
        print(
            f"[cognition:CALL] id={call_id} messages={len(messages)} temp={chat_args.get('temperature', '∅')} max_tokens={chat_args.get('max_tokens', '∅')}")


        # request-level timeout (seconds) – independent of client connect timeout

        try:
            _persist_snapshot(call_id, "preflight", {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "description": description,
                "provider": prov,
                "model": mdl,
                "parameters": {"temperature": chat_args.get("temperature", None),
                               "max_tokens": chat_args.get("max_tokens", None)},
                "messages_count": len(messages),
                "status": "about_to_call"
            })

            resp = client.chat.completions.create(**chat_args)
            # ---------- success path ----------
            content = ""
            try:
                content = resp.choices[0].message.content or ""
            except Exception:
                content = ""

            try:
                usage = {
                    "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                    "total_tokens": getattr(resp.usage, "total_tokens", None),
                }
            except Exception:
                usage = None

            try:
                resp_dump = resp.model_dump()
            except Exception:
                try:
                    resp_dump = resp.to_dict()
                except Exception:
                    resp_dump = str(resp)

            # Truncate massive payloads to avoid crashes
            _dump_str = None
            try:
                _dump_str = json.dumps(resp_dump)
            except Exception:
                _dump_str = str(resp_dump)
            if _dump_str and len(_dump_str) > 2_000_000:
                resp_dump = {"truncated": True, "note": "response too large to store safely"}

            exchange_record = {
                "call_id": call_id,
                "timestamp_utc": datetime.utcnow().isoformat(),
                "description": description,
                "provider": prov,
                "model": mdl,
                "base_url": _base_url(),
                "parameters": {"temperature": temp, "max_tokens": mx},
                "messages": messages,
                "response": resp_dump,
                "raw_text": content,
                "usage": usage,
                "error": None,
            }
            exchange_path = _persist_exchange(exchange_record)

            try:
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
                pass

            raw_out = content if isinstance(content, str) else str(content)
            print(f"[cognition:RETURN] id={call_id} len(raw_text)={len(raw_out)} usage={usage}")
            return CognitionResult(model_id=mdl, raw_text=raw_out, usage=usage, provider=prov)

        except Exception as e:
            # ---------- error path: ALWAYS persist a forensic record ----------
            err_info = {"type": type(e).__name__, "message": str(e)}
            try:
                import traceback as _tb
                err_info["traceback"] = _tb.format_exc()
            except Exception:
                pass

            exchange_record = {
                "call_id": call_id,
                "timestamp_utc": datetime.utcnow().isoformat(),
                "description": description,
                "provider": prov,
                "model": mdl,
                "base_url": _base_url(),
                "parameters": {"temperature": temp, "max_tokens": mx},
                "messages": messages,
                "response": None,
                "raw_text": "",
                "usage": None,
                "error": err_info,
            }
            exchange_path = _persist_exchange(exchange_record)
            print(f"[cognition:ERROR] id={call_id} persisted forensic record → {exchange_path}")
            raise

    # Approval gate: only now will the call happen
    result = approvals.request_approval(
        description=f"{description} | provider={prov} model={mdl}",
        call_fn=_do_call,
        timeout=timeout
    )
    if not result:
        _persist_snapshot(call_id, "denied_or_failed", {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "description": description,
            "provider": prov,
            "model": mdl,
            "status": "approval_denied_or_no_result"
        })
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
