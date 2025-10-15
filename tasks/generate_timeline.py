# tasks/generate_timeline.py
import os, json
from core.knowledge_space.timeline import build_timeline

OUT = "outputs/ks_timeline.json"

def run(root_path=None, guidance="", recall_depth=0, output_file=None, downloaded=False):
    sources = ["changelog"] if downloaded else None
    sessions = build_timeline(sources=sources)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, default=str)
    return True, f"Timeline generated with {len(sessions)} session(s). Saved to {OUT}"
