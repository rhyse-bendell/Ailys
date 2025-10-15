# tasks/export_timeline_csv.py
import os, csv, json, sqlite3, re
from datetime import datetime
from core.knowledge_space.storage import DB_PATH

# Optional run-scoped helpers
try:
    from core.knowledge_space.paths import ensure_run_dirs, new_run_id
except Exception:
    ensure_run_dirs = None  # type: ignore
    new_run_id = None       # type: ignore

LEGACY_OUT_PATH = os.path.join("outputs", "ks_timeline.csv")


def _auto_run_id() -> str:
    if new_run_id:
        return new_run_id()
    return datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")


def _added_text_from_diff(payload_json: str) -> str:
    """
    Extract a compact excerpt of added text from a unified diff in payload_json['diff'].
    """
    if not payload_json:
        return ""
    try:
        p = json.loads(payload_json)
    except Exception:
        return ""
    diff = p.get("diff") or []
    added_lines = []
    for line in diff:
        # skip diff headers
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:].strip())
    text = " ".join(added_lines)
    # squash whitespace & limit length
    text = re.sub(r"\s+", " ", text).strip()
    return text[:400]


def run(root_path=None, guidance="", recall_depth=0, output_file=None, downloaded=False, run_id: str | None = None):
    """
    Export a row-per-edit CSV of the entire timeline:
      columns: ts, actor, unit, action, source, summary, content_excerpt
    - If core/knowledge_space/paths.py is present, writes to:
        outputs/ks_runs/{label_safe}/{run_id}/csv/ks_timeline.csv
      and updates that run's meta.json.
    - Otherwise, writes to legacy outputs/ks_timeline.csv
    """
    root = root_path or os.getcwd()
    rid = run_id or _auto_run_id()

    # Decide output location (run-scoped if helpers are available)
    if ensure_run_dirs:
        run_base, sub = ensure_run_dirs(root, run_id=rid)
        out_path = os.path.join(sub["csv"], "ks_timeline.csv")
        meta_path = os.path.join(run_base, "meta.json")
    else:
        out_path = LEGACY_OUT_PATH
        meta_path = None

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT e.ts, e.actor, e.source, d.summary, d.payload_json
        FROM events e
        LEFT JOIN deltas d ON d.version_id = e.version_id
        ORDER BY e.ts ASC
    """).fetchall()
    conn.close()

    # We will keep both logs & filesystem in CSV; user can filter later
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ts", "actor", "unit", "action", "source", "summary", "content_excerpt"])
        for ts, actor, source, summary, payload_json in rows:
            unit = ""
            action = ""
            try:
                p = json.loads(payload_json or "{}")
                unit = p.get("mentioned_unit") or p.get("rel_path") or p.get("path") or ""
                action = p.get("action") or ""
            except Exception:
                pass
            excerpt = _added_text_from_diff(payload_json) if (source == "filesystem") else ""
            w.writerow([ts or "", actor or "", unit, action, source or "", (summary or "")[:500], excerpt])

    # Update run meta (if run-scoped)
    if meta_path:
        try:
            meta = json.load(open(meta_path, "r", encoding="utf-8"))
        except Exception:
            meta = {}
        meta["timeline_csv"] = out_path
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    return True, f"Timeline CSV written: {out_path}"
