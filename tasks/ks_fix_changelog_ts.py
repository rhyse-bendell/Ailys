# tasks/ks_fix_changelog_ts.py
import sqlite3
from core.knowledge_space.storage import DB_PATH
from core.knowledge_space.sniffers import parse_changelog_row

def run(root_path=None, guidance="", recall_depth=0, output_file=None, downloaded=False):
    """
    One-time (re)writer: for events where source='changelog',
    re-parse the raw row and overwrite events.ts with the true timestamp if found.
    Idempotent: re-running will only touch rows where ts differs from parsed.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT id, ts, raw
        FROM events
        WHERE source='changelog'
    """).fetchall()

    fixed = 0
    total = len(rows)
    for eid, ts_old, raw in rows:
        parsed = parse_changelog_row(raw or "")
        ts_new = parsed.get("ts")
        if not ts_new:
            continue
        ts_new_iso = ts_new.isoformat()
        if ts_new_iso != ts_old:
            c.execute("UPDATE events SET ts=? WHERE id=?", (ts_new_iso, eid))
            fixed += 1

    conn.commit()
    conn.close()
    return True, f"Changelog timestamp maintenance complete. Updated {fixed} of {total} events."
