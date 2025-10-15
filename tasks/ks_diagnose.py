# tasks/ks_diagnose.py
import sqlite3, json
from core.knowledge_space.storage import DB_PATH
from core.knowledge_space.participants import best_label, get_or_create_pid

def run(root_path=None, guidance="", recall_depth=0, output_file=None, downloaded=False):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()

    by_source = dict(c.execute("SELECT source, COUNT(*) FROM events GROUP BY source").fetchall())
    logs = c.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM events WHERE source='changelog'").fetchone()
    log_count, log_min, log_max = logs[0] or 0, logs[1], logs[2]

    # actor tallies
    actor_rows = c.execute("""
        SELECT actor, COUNT(*) FROM events
        WHERE actor IS NOT NULL AND TRIM(actor) <> ''
        GROUP BY actor ORDER BY COUNT(*) DESC
    """).fetchall()
    conn.close()

    lines = []
    lines.append("=== KS Diagnostics ===")
    lines.append(f"Events by source: {by_source}")
    lines.append(f"Changelog events: {log_count}, ts range: {log_min} → {log_max}")
    lines.append("Actors (PID → count):")
    for aid, cnt in actor_rows:
        pid = get_or_create_pid(aid)
        label = best_label(aid)
        lines.append(f"  - {pid} ({label}) : {cnt}")
    return True, "\n".join(lines)
