
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
