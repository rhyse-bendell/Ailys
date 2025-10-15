# core/config.py
import os
from typing import Dict, Tuple
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    # If python-dotenv isn't installed yet, the rest still works with os.environ.
    def load_dotenv(*args, **kwargs):
        return False

ENV_KEYS = [
    "OPENAI_API_KEY",
    "OPENALEX_EMAIL",
    "CROSSREF_MAILTO",
    "SEMANTIC_SCHOLAR_KEY",
    "NCBI_API_KEY",
    "LIT_RATE_LIMIT_SEC",
    "AILYS_APPROVAL_MODE",
]

def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "•" * len(value)
    return value[:3] + "•" * max(4, len(value) - 7) + value[-4:]

def load_env(env_path: str = "..env") -> Dict[str, str]:
    """
    Loads ..env (if present) and returns a dict of the keys we care about.
    """
    # Load file variables into process .env (non-fatal if missing)
    load_dotenv(dotenv_path=env_path, override=False)
    return {k: os.getenv(k, "") for k in ENV_KEYS}

def _read_env_file(env_path: str) -> Tuple[str, Dict[str, str]]:
    p = Path(env_path)
    contents = p.read_text(encoding="utf-8") if p.exists() else ""
    existing: Dict[str, str] = {}
    for line in contents.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        existing[k.strip()] = v.strip()
    return contents, existing

def save_env_updates(updates: Dict[str, str], env_path: str = "..env") -> None:
    """
    Idempotently update/add only the keys we manage. Keeps comments/other lines.
    """
    p = Path(env_path)
    contents, existing = _read_env_file(env_path)

    lines = contents.splitlines() if contents else []
    # map of key -> index in lines
    idx = {}
    for i, line in enumerate(lines):
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            idx[k] = i

    for k, v in updates.items():
        if k not in ENV_KEYS:
            continue
        if k in idx:
            lines[idx[k]] = f"{k}={v}"
        else:
            # ensure newline before appending if file exists and doesn't end with newline
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"{k}={v}")

        # also update the live process .env so the current session picks it up
        if v == "":
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    out = "\n".join(lines).rstrip() + ("\n" if lines else "")
    p.write_text(out, encoding="utf-8")
