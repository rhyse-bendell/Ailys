# core/knowledge_space/paths.py
import os, json, re, random, string
from datetime import datetime
from .storage import get_or_create_collection

RUNS_ROOT = os.path.join("outputs", "ks_runs")

def _safe(name: str) -> str:
    name = name.strip().replace("\\", "/")
    name = name.split("/")[-1]
    name = re.sub(r'[^a-zA-Z0-9._\- ]+', "_", name)
    return name[:80] if name else "collection"

def new_run_id() -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    suf = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{ts}_{suf}"

def ensure_run_dirs(root_path: str, run_id: str | None = None):
    """
    Create and return a run directory and subfolders for this knowledge space.
    """
    _, label = get_or_create_collection(root_path)
    label_safe = _safe(label or os.path.basename(root_path) or "collection")
    rid = run_id or new_run_id()
    base = os.path.join(RUNS_ROOT, label_safe, rid)
    os.makedirs(base, exist_ok=True)
    # standard subdirs
    sub = {
        "json": os.path.join(base, "json"),
        "csv": os.path.join(base, "csv"),
        "viz": os.path.join(base, "viz"),
        "units": os.path.join(base, "viz", "units"),
        "chunks": os.path.join(base, "json", "chunks"),
        "prompts": os.path.join(base, "json", "prompt_chunks"),
    }
    for p in sub.values():
        os.makedirs(p, exist_ok=True)

    # write meta.json if not present
    meta_path = os.path.join(base, "meta.json")
    if not os.path.exists(meta_path):
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "root_path": root_path,
                "label": label,
                "label_safe": label_safe,
                "run_id": rid,
                "created_utc": datetime.utcnow().isoformat()
            }, f, indent=2)
    return base, sub
