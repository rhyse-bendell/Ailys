# core/knowledge_space/participants.py
import sqlite3, os
from .storage import DB_PATH

def _ensure_schema(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        actor_id TEXT PRIMARY KEY,       -- e.g., 'people/106933262117653156301'
        pid TEXT NOT NULL,               -- e.g., 'PID001'
        display_name TEXT,               -- optional friendly name (can be NULL)
        first_seen_ts TEXT               -- ISO timestamp of first time we saw this actor, nullable
    )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_participants_pid ON participants(pid)")
    conn.commit()

def _next_pid(conn: sqlite3.Connection) -> str:
    cur = conn.execute("SELECT pid FROM participants ORDER BY pid DESC LIMIT 1")
    row = cur.fetchone()
    if not row or not row[0]:
        return "PID001"
    # row like 'PID007' -> next
    try:
        n = int(row[0].replace("PID", "")) + 1
    except Exception:
        # fallback: count
        cur = conn.execute("SELECT COUNT(*) FROM participants")
        n = (cur.fetchone()[0] or 0) + 1
    return f"PID{n:03d}"

def get_or_create_pid(actor_id: str, first_seen_ts: str | None = None) -> str:
    """
    Returns a stable PID for a given actor_id. Creates an entry if needed.
    """
    if not actor_id:
        return ""  # anonymous / unknown
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_schema(conn)
        cur = conn.execute("SELECT pid FROM participants WHERE actor_id=?", (actor_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        pid = _next_pid(conn)
        conn.execute(
            "INSERT INTO participants(actor_id, pid, display_name, first_seen_ts) VALUES (?,?,?,?)",
            (actor_id, pid, None, first_seen_ts)
        )
        conn.commit()
        return pid
    finally:
        conn.close()

def best_label(actor_id: str) -> str:
    """
    Prefer display_name if set; else PID; else a short actor_id tail.
    """
    if not actor_id:
        return ""
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_schema(conn)
        cur = conn.execute("SELECT pid, COALESCE(display_name,'') FROM participants WHERE actor_id=?", (actor_id,))
        row = cur.fetchone()
        if row:
            pid, name = row
            return name or pid
        # not registered yet -> synthesize tail label
        tail = actor_id.split("/")[-1]
        return f"{tail[:6]}…"
    finally:
        conn.close()

def backfill_all_participants():
    """
    Scan events table for all distinct actor_ids and ensure each has a PID.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_schema(conn)
        rows = conn.execute("""
            SELECT DISTINCT actor, MIN(ts) AS first_ts
            FROM events
            WHERE actor IS NOT NULL AND TRIM(actor) <> ''
            GROUP BY actor
            ORDER BY first_ts ASC
        """).fetchall()
        created = 0
        for actor_id, first_ts in rows:
            cur = conn.execute("SELECT 1 FROM participants WHERE actor_id=?", (actor_id,))
            if not cur.fetchone():
                pid = _next_pid(conn)
                conn.execute(
                    "INSERT INTO participants(actor_id, pid, display_name, first_seen_ts) VALUES (?,?,?,?)",
                    (actor_id, pid, None, first_ts)
                )
                created += 1
        conn.commit()
        return created, len(rows)
    finally:
        conn.close()
