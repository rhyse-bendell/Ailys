import sqlite3
from datetime import datetime, timedelta
from .storage import DB_PATH

def _fetch_events(db: str = DB_PATH, sources=None):
    conn = sqlite3.connect(db); c = conn.cursor()
    if sources:
        qmarks = ",".join("?" for _ in sources)
        rows = c.execute(
            f"SELECT id, event_type, artifact_id, version_id, actor, ts, source FROM events "
            f"WHERE source IN ({qmarks}) ORDER BY ts ASC", tuple(sources)
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT id, event_type, artifact_id, version_id, actor, ts, source FROM events ORDER BY ts ASC"
        ).fetchall()
    conn.close()
    events = []
    for (id_, et, aid, vid, actor, ts, source) in rows:
        try:
            ts_dt = datetime.fromisoformat(ts)
        except Exception:
            continue
        events.append({"id":id_, "event_type":et, "artifact_id":aid, "version_id":vid,
                       "actor":actor or "", "ts": ts_dt, "source": source})
    return events

def build_timeline(idle_minutes=10, sources=None):
    events = _fetch_events(sources=sources)
    if not events: return []
    events.sort(key=lambda e: e["ts"])
    sessions, current = [], []
    last_ts = events[0]["ts"]

    for e in events:
        if (e["ts"] - last_ts) > timedelta(minutes=idle_minutes) and current:
            sessions.append({
                "start": current[0]["ts"].isoformat(),
                "end":   current[-1]["ts"].isoformat(),
                "events": [{**x, "ts": x["ts"].isoformat()} for x in current]
            })
            current = []
        current.append(e); last_ts = e["ts"]

    if current:
        sessions.append({
            "start": current[0]["ts"].isoformat(),
            "end":   current[-1]["ts"].isoformat(),
            "events": [{**x, "ts": x["ts"].isoformat()} for x in current]
        })
    return sessions
