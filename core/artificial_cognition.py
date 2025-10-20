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

# --- Model profiles & helpers -------------------------------------------------

def _token_param_for(prov: str, model: str) -> str:
    """
    Return the correct token-limit parameter name for this model/provider.
    """
    m = (model or "").lower().strip()
    if prov == "openai" and m.startswith("gpt-5"):
        return "max_completion_tokens"
    return "max_tokens"  # 4o/4.x and most openai_compatible servers

def _should_drop_temperature(prov: str, model: str, temperature: Optional[float]) -> bool:
    """
    Some models (e.g., OpenAI gpt-5) ignore or reject custom temperature.
    """
    if prov == "openai" and model.lower().startswith("gpt-5"):
        return True
    return False


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

def _persist_snapshot(call_id: str, suffix: str, payload: Dict[str, Any], *, run_dir: Optional[Path] = None, seq: Optional[List[int]] = None) -> str:
    """
    Write a small JSON snapshot for a stage in the lifecycle (queued, preflight, denied, etc.).
    If run_dir/seq are provided, files are written inside that folder with a 000-, 001-, ... prefix.
    Otherwise we fall back to the old flat "<utc>_<callid>_<suffix>.json" behavior.
    Always best-effort; never throws.
    """
    try:
        base = _exchanges_dir()
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        if run_dir is None:
            path = base / f"{ts}_{call_id}_{suffix}.json"
        else:
            run_dir.mkdir(parents=True, exist_ok=True)
            # sequence handling
            if seq is not None and len(seq) == 1:
                n = seq[0]
                seq[0] += 1
            else:
                n = 0
            path = run_dir / f"{n:03d}_{suffix}.json"

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



def _persist_exchange(record: Dict[str, Any], *, run_dir: Optional[Path] = None, seq: Optional[List[int]] = None, filename_hint: Optional[str] = None) -> str:
    """
    Write the full exchange record as JSON and return the absolute path.
    If run_dir/seq are provided, write into that folder with sequence prefix and optional filename_hint.
    Otherwise fall back to legacy flat naming.
    """
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    sid = uuid.uuid4().hex[:8]

    if run_dir is None:
        path = _exchanges_dir() / f"{ts}_{sid}.json"
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
        if seq is not None and len(seq) == 1:
            n = seq[0]
            seq[0] += 1
        else:
            n = 0
        hint = f"_{filename_hint}" if filename_hint else ""
        path = run_dir / f"{n:03d}{hint}.json"

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        print(f"[cognition:PERSIST] wrote exchange JSON → {path}")
    except Exception as e:
        print(f"[cognition:PERSIST] ERROR writing {path}: {e}")
        print(traceback.format_exc())
    return str(path.resolve())


def _with_arg(args: Dict[str, Any], key: str, value: Any, *, remove: Optional[List[str]] = None) -> Dict[str, Any]:
    out = dict(args)
    out[key] = value
    for k in (remove or []):
        out.pop(k, None)
    return out

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

    # Per-run folder + sequence counter (ensures every artifact for this call stays together)
    run_ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    run_dir = _exchanges_dir() / f"{run_ts}_{call_id}"
    seq = [0]  # monotonic counter for files in run_dir

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
    }, run_dir=run_dir, seq=seq)

    def _do_call(overrides: Optional[Dict[str, Any]] = None) -> CognitionResult:
        # We only import and read keys *inside* the call to respect approval gating.
        try:
            from openai import OpenAI
        except Exception as e:
            raise RuntimeError(f"OpenAI SDK not available: {e}")

        # --- Apply approval-time overrides (model, token cap, timeout) -------------
        eff_model = (overrides or {}).get("model", mdl)
        eff_timeout = (overrides or {}).get("timeout", None)
        ov_max_tokens = (overrides or {}).get("max_tokens", None)
        ov_max_completion_tokens = (overrides or {}).get("max_completion_tokens", None)
        eff_mx = ov_max_tokens if ov_max_tokens is not None else (
            ov_max_completion_tokens if ov_max_completion_tokens is not None else mx)

        # Build client
        kwargs = {}
        if prov == "openai_compatible":
            if base_url:
                kwargs["base_url"] = base_url
            if api_key:
                kwargs["api_key"] = api_key
        else:
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set. Add it in the Config tab.")
            kwargs["api_key"] = api_key

        if "timeout" not in kwargs:
            kwargs["timeout"] = eff_timeout if isinstance(eff_timeout, (int, float)) else _llm_timeout()

        # Disable SDK-level retries: approval = one HTTP call
        kwargs["max_retries"] = 0
        client = OpenAI(**kwargs)

        # Build chat args using the (possibly overridden) model
        chat_args: Dict[str, Any] = {
            "model": eff_model,
            "messages": messages,
        }

        # temperature policy
        if not _should_drop_temperature(prov, eff_model, temp):
            chat_args["temperature"] = temp
        else:
            print("[cognition:CALL] dropping temperature per model profile")

        # token-limit field per model (re-evaluated for eff_model)
        token_param = _token_param_for(prov, eff_model)
        if eff_mx is not None:
            chat_args[token_param] = eff_mx
        if token_param == "max_completion_tokens":
            chat_args.pop("max_tokens", None)
        else:
            chat_args.pop("max_completion_tokens", None)

        # Diagnostics
        print(f"[cognition:CALL] provider={prov} model={eff_model} base_url={_base_url() or ''}")
        print(f"[cognition:CALL] cwd={Path.cwd()}  exchanges_base={_resolve_exchanges_base()}")
        print(f"[cognition:CALL] id={call_id} messages={len(messages)} "
              f"temp={chat_args.get('temperature', '∅')} "
              f"max_tokens={chat_args.get('max_tokens', '∅')} "
              f"max_completion_tokens={chat_args.get('max_completion_tokens', '∅')}")

        # ---- Helpers for per-attempt logging and execution -----------------------
        def _single_call(attempt_idx: int, args: Dict[str, Any], attempt_tag: str) -> CognitionResult:
            _persist_snapshot(call_id, f"{attempt_tag}_preflight", {
                "timestamp_utc": datetime.utcnow().isoformat(),
                "description": description,
                "provider": prov,
                "model": args.get("model", eff_model),
                "parameters": {
                    "temperature": args.get("temperature"),
                    "max_tokens": args.get("max_tokens"),
                    "max_completion_tokens": args.get("max_completion_tokens"),
                },
                "messages_count": len(messages),
                "status": "about_to_call"
            }, run_dir=run_dir, seq=seq)

            resp = client.chat.completions.create(**args)

            # --- Extract content (chat.completions) and usage
            # NOTE: If we ever switch endpoints, this code will intentionally expose a "no text but tokens > 0"
            # situation with a high-signal error message below.
            try:
                content = resp.choices[0].message.content or ""
            except Exception:
                content = ""

            # usage
            try:
                usage = {
                    "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                    "total_tokens": getattr(resp.usage, "total_tokens", None),
                }
            except Exception:
                usage = None

            # structured dump for forensics
            try:
                resp_dump = resp.model_dump()
            except Exception:
                try:
                    resp_dump = resp.to_dict()
                except Exception:
                    resp_dump = str(resp)

            # response shape breadcrumb (helps triage when empty content)
            try:
                top_keys = list(resp_dump.keys()) if isinstance(resp_dump, dict) else []
            except Exception:
                top_keys = []

            # mark truncation if we hit the configured cap
            provided_cap = args.get("max_completion_tokens", args.get("max_tokens"))
            if usage and isinstance(usage.get("completion_tokens"), int) and isinstance(provided_cap, int):
                if usage["completion_tokens"] >= provided_cap:
                    usage["truncated"] = True
                    print(
                        f"[cognition:INFO] id={call_id} attempt={attempt_idx} – output likely truncated by token cap ({usage['completion_tokens']}/{provided_cap}).")

            # Truncate massive payloads
            try:
                _s = json.dumps(resp_dump)
            except Exception:
                _s = str(resp_dump)
            if _s and len(_s) > 2_000_000:
                resp_dump = {"truncated": True, "note": "response too large to store safely"}

            _persist_exchange({
                "call_id": call_id,
                "attempt": attempt_idx,
                "timestamp_utc": datetime.utcnow().isoformat(),
                "description": description,
                "provider": prov,
                "model": args.get("model", eff_model),
                "base_url": _base_url(),
                "parameters": {
                    "temperature": args.get("temperature"),
                    "max_tokens": args.get("max_tokens"),
                    "max_completion_tokens": args.get("max_completion_tokens"),
                },
                "messages": messages,
                "response": resp_dump,
                "raw_text": content,
                "usage": usage,
                "error": None,
            }, run_dir=run_dir, seq=seq, filename_hint=f"exchange_attempt{attempt_idx}")


            raw_out = content if isinstance(content, str) else str(content)

            # If the model says it generated tokens but we got no text, surface a precise, actionable error.
            if (not raw_out.strip()) and usage and isinstance(usage.get("completion_tokens"), int) and usage[
                "completion_tokens"] > 0:
                # Keep file name of the last persisted exchange for breadcrumbing
                last_path = _persist_exchange({
                    "call_id": call_id,
                    "attempt": attempt_idx,
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "description": f"{description} (empty-text anomaly record)",
                    "provider": prov,
                    "model": args.get("model", eff_model),
                    "base_url": _base_url(),
                    "parameters": {
                        "temperature": args.get("temperature"),
                        "max_tokens": args.get("max_tokens"),
                        "max_completion_tokens": args.get("max_completion_tokens"),
                    },
                    "messages": messages,
                    "response": resp_dump,
                    "raw_text": raw_out,
                    "usage": usage,
                    "error": {
                        "type": "EmptyTextWithTokenUsage",
                        "message": "No plain text returned, but completion_tokens > 0. This usually means truncation by token cap OR a non-text/tool response shape.",
                        "response_top_keys": top_keys,
                    },
                }, run_dir=run_dir, seq=seq, filename_hint=f"exchange_attempt{attempt_idx}_empty_text")

                # Build human-friendly diagnostic
                cap_name = "max_completion_tokens" if "max_completion_tokens" in args else "max_tokens"
                cap_val = args.get(cap_name)
                truncated_note = ""
                if usage.get("truncated"):
                    truncated_note = f" (likely truncated at {cap_name}={cap_val})"

                raise RuntimeError(
                    "Model returned no plain text, but reported token usage."
                    f"{truncated_note}\n"
                    f"completion_tokens={usage.get('completion_tokens')}, prompt_tokens={usage.get('prompt_tokens')}, total_tokens={usage.get('total_tokens')}\n"
                    f"Response keys: {top_keys}\n"
                    f"Forensics saved to: {last_path}"
                )

            print(f"[cognition:RETURN] id={call_id} attempt={attempt_idx} len(raw_text)={len(raw_out)} usage={usage}")
            return CognitionResult(model_id=args.get("model", eff_model), raw_text=raw_out, usage=usage, provider=prov)

        def _describe_fix(reason: str, fix: str, args_after: Dict[str, Any]) -> str:
            params_preview = {
                "temperature": args_after.get("temperature"),
                "max_tokens": args_after.get("max_tokens"),
                "max_completion_tokens": args_after.get("max_completion_tokens"),
            }
            return (f"Retry with adjusted parameters for {eff_model}: {fix}\n"
                    f"Reason: {reason}\n"
                    f"Would call with: {params_preview}")

        # ---- Attempt loop (initial + retries gated separately) -------------------
        MAX_ATTEMPTS = 3
        attempt = 1
        args = dict(chat_args)

        while attempt <= MAX_ATTEMPTS:
            tag = "attempt1" if attempt == 1 else f"retry{attempt - 1}"
            try:
                if attempt == 1:
                    # First attempt uses approval of the original request
                    return _single_call(attempt, args, tag)
                else:
                    # Retry requires separate approval (already implemented above in your code)
                    retry_desc = current_retry_desc  # set when we crafted the fix
                    approved_result = approvals.request_approval(
                        description=retry_desc,
                        call_fn=lambda ov=None: _single_call(attempt, args, tag),
                        timeout=timeout
                    )
                    if not approved_result:
                        _persist_snapshot(call_id, f"{tag}_denied_or_failed", {
                            "timestamp_utc": datetime.utcnow().isoformat(),
                            "description": retry_desc,
                            "provider": prov,
                            "model": args.get("model", eff_model),
                            "status": "approval_denied_or_no_result"
                        }, run_dir=run_dir, seq=seq)
                        raise RuntimeError("Retry approval declined or failed; no result returned.")
                    if not isinstance(approved_result, CognitionResult):
                        raise RuntimeError(f"Unexpected retry result type: {type(approved_result)!r}")
                    return approved_result

            except Exception as e:
                # Persist forensic record for this failed attempt
                err_info = {"type": type(e).__name__, "message": str(e)}
                try:
                    import traceback as _tb
                    err_info["traceback"] = _tb.format_exc()
                except Exception:
                    pass

                _persist_exchange({
                    "call_id": call_id,
                    "attempt": attempt,
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "description": description,
                    "provider": prov,
                    "model": args.get("model", eff_model),
                    "base_url": _base_url(),
                    "parameters": {
                        "temperature": args.get("temperature"),
                        "max_tokens": args.get("max_tokens"),
                        "max_completion_tokens": args.get("max_completion_tokens"),
                    },
                    "messages": messages,
                    "response": None,
                    "raw_text": "",
                    "usage": None,
                    "error": err_info,
                }, run_dir=run_dir, seq=seq, filename_hint=f"exchange_attempt{attempt_idx}")

                if attempt >= MAX_ATTEMPTS:
                    print(f"[cognition:ERROR] id={call_id} attempt={attempt} – no more retries.")
                    raise

                reason = str(e)
                fix_desc = None
                new_args = None

                # Heuristics for common OpenAI errors
                if "Unsupported parameter" in reason and "max_tokens" in reason:
                    new_args = dict(args);
                    new_args.pop("max_tokens", None);
                    new_args["max_completion_tokens"] = eff_mx or mx
                    fix_desc = "swap max_tokens → max_completion_tokens"
                elif "Unsupported parameter" in reason and "max_completion_tokens" in reason:
                    new_args = dict(args);
                    new_args.pop("max_completion_tokens", None);
                    new_args["max_tokens"] = eff_mx or mx
                    fix_desc = "swap max_completion_tokens → max_tokens"

                if (fix_desc is None) and ("temperature" in reason.lower()) and ("unsupported" in reason.lower()):
                    if "temperature" in args:
                        new_args = dict(args);
                        new_args.pop("temperature", None)
                        fix_desc = "drop temperature"

                if (fix_desc is None) and any(
                        s in reason.lower() for s in ("too many tokens", "context length", "maximum context")):
                    if "max_completion_tokens" in args and isinstance(args["max_completion_tokens"], int):
                        new_args = dict(args);
                        new_args["max_completion_tokens"] = max(256, args["max_completion_tokens"] // 2)
                        fix_desc = "halve max_completion_tokens"
                    elif "max_tokens" in args and isinstance(args["max_tokens"], int):
                        new_args = dict(args);
                        new_args["max_tokens"] = max(256, args["max_tokens"] // 2)
                        fix_desc = "halve max_tokens"

                if new_args is None:
                    print(f"[cognition:ERROR] id={call_id} attempt={attempt} – no known fix; re-raising.")
                    raise

                current_retry_desc = f"Retry {attempt}/{MAX_ATTEMPTS - 1}: " + _describe_fix(reason, fix_desc, new_args)
                _persist_snapshot(call_id, f"{tag}_requested", {
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "description": current_retry_desc,
                    "provider": prov,
                    "model": args.get("model", eff_model),
                    "parameters_before": {
                        "temperature": args.get("temperature"),
                        "max_tokens": args.get("max_tokens"),
                        "max_completion_tokens": args.get("max_completion_tokens"),
                    },
                    "parameters_after": {
                        "temperature": new_args.get("temperature"),
                        "max_tokens": new_args.get("max_tokens"),
                        "max_completion_tokens": new_args.get("max_completion_tokens"),
                    },
                    "status": "retry_requested"
                }, run_dir=run_dir, seq=seq)

                args = new_args
                attempt += 1

        raise RuntimeError("Exhausted attempts without a result.")

    # === Approval gate (initial call) ==========================================
    # Try module-level helper first, then fall back to the instance on approval_queue
    request_approval_fn = getattr(approvals, "request_approval", None)
    if not callable(request_approval_fn):
        request_approval_fn = getattr(approvals.approval_queue, "request_approval", None)

    if not callable(request_approval_fn):
        _persist_snapshot(call_id, "denied_or_failed", {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "description": description,
            "provider": prov,
            "model": mdl,
            "status": "no_request_approval_function"
        }, run_dir=run_dir, seq=seq)
        raise RuntimeError("Approval system not available: request_approval function not found.")

    # Record that we're enqueueing this call for approval
    _persist_snapshot(call_id, "enqueue", {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "description": description,
        "provider": prov,
        "model": mdl,
        "status": "enqueue_request"
    }, run_dir=run_dir, seq=seq)
    print("[cognition:APPROVAL] Enqueuing approval for cognition call...")

    # Enqueue and wait for user approval (or auto/dryrun per mode)
    result = request_approval_fn(
        description=f"{description} | provider={prov} model={mdl}",
        call_fn=_do_call,
        timeout=timeout
    )

    # Record the approval return path (forensics if it returns None)
    _persist_snapshot(call_id, "approval_returned", {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "description": description,
        "provider": prov,
        "model": mdl,
        "status": "approval_returned",
        "result_type": (type(result).__name__ if result is not None else "None")
    }, run_dir=run_dir, seq=seq)
    print(f"[cognition:APPROVAL] Approval returned with type="
          f"{type(result).__name__ if result is not None else 'None'}")

    if not result:
        _persist_snapshot(call_id, "denied_or_failed", {
            "timestamp_utc": datetime.utcnow().isoformat(),
            "description": description,
            "provider": prov,
            "model": mdl,
            "status": "approval_denied_or_no_result"
        }, run_dir=run_dir, seq=seq)
        raise RuntimeError("Approval declined or failed; no result returned.")

    if not isinstance(result, CognitionResult):
        raise RuntimeError(f"Artificial cognition returned unexpected type: {type(result)!r}")

    return result

# ------------------------------ Convenience --------------------------------

def model_summary() -> str:
    """Small helper for GUI: shows current brain selection."""
    prov, mdl, burl = _provider(), _model(), _base_url() or ""
    if prov == "openai_compatible" and burl:
        return f"{mdl} @ {burl}"
    return mdl
