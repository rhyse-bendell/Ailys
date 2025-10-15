# tasks/compute_metrics.py
import os, csv, json, sqlite3, re
from datetime import datetime
from collections import defaultdict
from core.knowledge_space.storage import DB_PATH
from core.knowledge_space.participants import best_label, get_or_create_pid

# Optional run-scoped helpers
try:
    from core.knowledge_space.paths import ensure_run_dirs, new_run_id
except Exception:
    ensure_run_dirs = None  # type: ignore
    new_run_id = None       # type: ignore

LEGACY_OUT_PATH = os.path.join("outputs", "ks_metrics_by_actor.csv")

def _auto_run_id() -> str:
    if new_run_id:
        return new_run_id()
    return datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")

_word_re = re.compile(r"\w+", flags=re.UNICODE)

def _count_words_from_diff(payload_json: str) -> int:
    if not payload_json:
        return 0
    try:
        p = json.loads(payload_json)
    except Exception:
        return 0
    diff = p.get("diff") or []
    added = []
    for line in diff:
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added += _word_re.findall(line[1:])
    return len(added)

def _count_words_from_log_content(payload_json: str) -> int:
    if not payload_json:
        return 0
    try:
        p = json.loads(payload_json)
    except Exception:
        return 0
    content = p.get("content") or ""
    if not content:
        return 0
    return len(_word_re.findall(content))

def run(root_path=None, guidance="", recall_depth=0, output_file=None, downloaded=False, run_id: str | None = None):
    """
    Computes per-actor metrics:
      - total_edits (all sources)
      - words_added (filesystem text diffs)
      - words_added_logs (from bracketed activity logs with content)
      - total_words_added = words_added + words_added_logs
      - first_ts, last_ts, minutes_span, edits_per_minute
    """
    root = root_path or os.getcwd()
    rid = run_id or _auto_run_id()

    if ensure_run_dirs:
        run_base, sub = ensure_run_dirs(root, run_id=rid)
        out_path = os.path.join(sub["csv"], "ks_metrics_by_actor.csv")
        meta_path = os.path.join(run_base, "meta.json")
    else:
        out_path = LEGACY_OUT_PATH
        meta_path = None

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT e.ts, e.actor, e.source, d.kind, d.payload_json
        FROM events e
        LEFT JOIN deltas d ON d.version_id = e.version_id
        ORDER BY e.ts ASC
    """).fetchall()
    conn.close()

    per = defaultdict(lambda: {
        "actor_id": "",
        "actor_label": "",
        "total_edits": 0,
        "words_added_fs": 0,
        "words_added_logs": 0,
        "first_ts": None,
        "last_ts": None
    })

    for ts, actor, source, kind, payload_json in rows:
        actor_id = actor or ""
        pid = get_or_create_pid(actor_id, first_seen_ts=ts) if actor_id else ""
        label = best_label(actor_id) if actor_id else "UNKNOWN"
        rec = per[label]
        rec["actor_id"] = actor_id
        rec["actor_label"] = label
        rec["total_edits"] += 1

        # Count true text diffs
        if source == "filesystem" and (kind == "text_edit"):
            rec["words_added_fs"] += _count_words_from_diff(payload_json)

        # Count bracketed activity content
        if source == "changelog" and (kind == "log_content"):
            rec["words_added_logs"] += _count_words_from_log_content(payload_json)

        # timestamps
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            dt = None
        if dt:
            if rec["first_ts"] is None or dt < rec["first_ts"]:
                rec["first_ts"] = dt
            if rec["last_ts"] is None or dt > rec["last_ts"]:
                rec["last_ts"] = dt

    # finalize & write
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "actor_label", "actor_id",
            "total_edits", "words_added_fs", "words_added_logs", "total_words_added",
            "first_ts", "last_ts", "minutes_span", "edits_per_minute"
        ])
        for label, rec in sorted(per.items(), key=lambda x: x[0]):
            first_ts = rec["first_ts"]
            last_ts = rec["last_ts"]
            minutes_span = 0.0
            if first_ts and last_ts:
                minutes_span = max(1.0, (last_ts - first_ts).total_seconds() / 60.0)
            edits_per_min = rec["total_edits"] / minutes_span if minutes_span > 0 else rec["total_edits"]
            total_words = rec["words_added_fs"] + rec["words_added_logs"]
            w.writerow([
                label,
                rec["actor_id"],
                rec["total_edits"],
                rec["words_added_fs"],
                rec["words_added_logs"],
                total_words,
                first_ts.isoformat() if first_ts else "",
                last_ts.isoformat() if last_ts else "",
                f"{minutes_span:.2f}",
                f"{edits_per_min:.4f}"
            ])

    if meta_path:
        try:
            meta = json.load(open(meta_path, "r", encoding="utf-8"))
        except Exception:
            meta = {}
        meta["metrics_csv"] = out_path
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    return True, f"Metrics CSV written: {out_path}"
