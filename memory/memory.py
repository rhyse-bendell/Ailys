
import json
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "crystallized_memory.jsonl"

def save_memory_event(event_type, source_text, ai_insight, user_input=None, tags=None, file_path=None):
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "source_text": source_text.strip()[:3000],
        "ai_insight": ai_insight.strip(),
        "user_input": user_input.strip() if user_input else None,
        "tags": tags or [],
        "file_path": file_path
    }

    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def get_all_memories():
    if not MEMORY_FILE.exists():
        return []
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def get_memories_by_tag(tag: str):
    return [m for m in get_all_memories() if tag in m.get("tags", [])]

def get_ai_insights_by_tag(tag: str):
    return [m["ai_insight"] for m in get_memories_by_tag(tag) if "ai_insight" in m]

# ==== Cognition exchange helpers (START) ====
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

_EXCH_DIR = Path(__file__).parent / "exchanges"

def list_exchanges(limit: Optional[int] = 100) -> List[Path]:
    """
    Return the most recent exchange files (sorted newest-first).
    """
    if not _EXCH_DIR.exists():
        return []
    files = sorted(_EXCH_DIR.glob("*.json"), key=lambda p: p.name, reverse=True)
    return files[:limit] if limit is not None else files

def load_exchange(path_or_name: str) -> Dict[str, Any]:
    """
    Load a single persisted exchange JSON by absolute path or file name.
    """
    p = Path(path_or_name)
    if not p.is_absolute():
        p = _EXCH_DIR / p.name
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def get_memories_by_type(event_type: str):
    """
    Convenience: filter crystallized memory by event_type (e.g., 'cognition_exchange').
    """
    return [m for m in get_all_memories() if m.get("event_type") == event_type]

def find_exchanges_by_model(model_substr: str, limit: Optional[int] = 100) -> List[Path]:
    """
    Simple filename scan; for richer filters, open JSON and inspect 'model' / 'description'.
    """
    model_substr = (model_substr or "").lower()
    results: List[Path] = []
    for p in list_exchanges(limit=None):
        try:
            with open(p, "r", encoding="utf-8") as f:
                j = json.load(f)
            if model_substr in str(j.get("model", "")).lower():
                results.append(p)
                if limit is not None and len(results) >= limit:
                    break
        except Exception:
            continue
    return results
# ==== Ailys patch: cognition exchange helpers (END) ====
