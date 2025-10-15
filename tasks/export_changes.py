# tasks/export_changes.py
import os
from datetime import datetime

# Use the main exporter (not the backup)
from core.knowledge_space.export import export_changes

# Optional: run-id helper if paths.py is present; else we synthesize one
try:
    from core.knowledge_space.paths import new_run_id
except Exception:
    new_run_id = None  # type: ignore


def _auto_run_id() -> str:
    if new_run_id:
        return new_run_id()
    # fallback: timestamp-only run id
    return datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")


def run(root_path=None, guidance: str = "", recall_depth: int = 0,
        output_file=None, downloaded: bool = False, run_id: str | None = None):
    """
    Export Knowledge Space changes to JSON/JSONL (+ compact/chunks).
    - Works even if caller does not pass root_path: defaults to current working directory.
    - Auto-generates a run_id so outputs never overwrite.
    - If 'downloaded' is True, export only 'changelog' events; else export all sources.
    """
    # Make it zero-config for callers:
    root = root_path or os.getcwd()
    rid = run_id or _auto_run_id()
    sources = ["changelog"] if downloaded else None

    produced_paths = export_changes(
        sources=sources,
        gap_minutes=30,
        make_compact=True,
        compact_summary_chars=160,
        max_lines_per_chunk=2000,  # adjust if you want smaller/larger shards
        root_path=root,            # <-- triggers collection/run-scoped output layout
        run_id=rid                 # <-- keeps all files grouped per run
    )

    # export_changes returns a list of produced files (or (list, run_base) depending on version);
    # normalize to list of strings for display:
    if isinstance(produced_paths, tuple) and len(produced_paths) >= 1:
        produced_list = produced_paths[0]
    else:
        produced_list = produced_paths

    header = f"Exported changes (run_id={rid}):"
    return True, header + "\n" + "\n".join(f"- {p}" for p in produced_list)
