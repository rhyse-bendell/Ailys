# core/knowledge_space/export_backup.py
import os, json, sqlite3, gzip
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from .storage import DB_PATH
from .participants import get_or_create_pid, best_label

OUT_DIR = "outputs"
ESSENTIAL_FIELDS = ("ts", "actor_label", "unit", "action", "summary", "source")

# -------------- helpers --------------

def _parse_iso(ts: str):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None

def _normalize_row(ts, actor, source, summary, payload_json, artifact_id, version_id):
    unit = None
    root_label = None
    rel_path = None
    path = None
    action = None
    extras = None

    if payload_json:
        try:
            p = json.loads(payload_json)
        except Exception:
            p = {}
        unit = p.get("mentioned_unit") or p.get("rel_path") or p.get("path")
        root_label = p.get("root_label")
        rel_path = p.get("rel_path")
        path = p.get("path")
        action = p.get("action")
        extras = p.get("extras")

    if unit and isinstance(unit, str):
        unit = unit.replace("\\", "/")
    if not unit:
        unit = (artifact_id or "")[:8]

    # Ensure a PID exists (auto-assign if actor present)
    actor_id = actor or ""
    actor_pid = ""
    actor_label = ""
    if actor_id:
        actor_pid = get_or_create_pid(actor_id, first_seen_ts=ts)
        actor_label = best_label(actor_id)  # display_name if set, else PID
    else:
        actor_label = "UNKNOWN"

    # short tag from label (for plots if needed)
    parts = [q for q in actor_label.replace(".", " ").replace("_", " ").split() if q]
    actor_tag = (parts[0][:3] if len(parts) == 1 else "".join(q[0] for q in parts)[:3]) or "?"

    return {
        "ts": ts,
        "actor": actor_id,
        "actor_pid": actor_pid,
        "actor_label": actor_label,      # preferred for narratives
        "actor_tag": actor_tag,
        "source": source or "",
        "action": action or "",
        "summary": (summary or "")[:500],
        "unit": unit or "",
        "root_label": root_label or "",
        "rel_path": rel_path or "",
        "path": path or "",
        "artifact_id": artifact_id or "",
        "version_id": version_id or "",
        "extras": extras or {},
    }

def _fetch_changes_raw():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT e.ts, e.actor, e.source, d.summary, d.payload_json, e.artifact_id, e.version_id
        FROM events e
        LEFT JOIN deltas d ON d.version_id = e.version_id
        ORDER BY e.ts ASC
    """).fetchall()
    conn.close()
    return rows

def _dedup_and_backfill(records):
    """
    Deduplicate rows that show up both under the log file path and the target unit.
    Key = (ts, summary). Prefer the row that has a 'mentioned_unit' and/or a non-UNKNOWN actor_label.
    Then backfill actor_label for its duplicate if needed.
    """
    # Build working structures with extra flags
    work = []
    for ts, actor, source, summary, payload_json, aid, vid in records:
        if not ts or not summary:
            # keep anyway but will be less helpful
            pass
        rec = _normalize_row(ts, actor, source, summary, payload_json, aid, vid)
        # easy flag: whether this row directly references mentioned unit
        has_mentioned = False
        if payload_json:
            try:
                pj = json.loads(payload_json)
                has_mentioned = bool(pj.get("mentioned_unit"))
            except Exception:
                pass
        rec["_has_mentioned_unit"] = has_mentioned
        rec["_payload_json"] = payload_json
        work.append(rec)

    # Bucket by (ts, summary)
    buckets = defaultdict(list)
    for r in work:
        buckets[(r["ts"], r["summary"])].append(r)

    cleaned = []
    for key, group in buckets.items():
        if len(group) == 1:
            cleaned.append(group[0])
            continue

        # Prefer one with mentioned_unit
        preferred = None
        for g in group:
            if g["_has_mentioned_unit"]:
                preferred = g
                break
        if not preferred:
            # Prefer non-UNKNOWN actor_label
            for g in group:
                if g["actor_label"] != "UNKNOWN":
                    preferred = g
                    break
        if not preferred:
            preferred = group[0]

        # Backfill minimal fields onto others (for consistency; we only emit one row though)
        # If you ever want to preserve both, you could mark duplicates.
        cleaned.append(preferred)

    # Sort again by ts
    cleaned.sort(key=lambda r: r["ts"])
    return cleaned

def _sessionize(records, gap_minutes=30):
    if not records:
        return []
    recs = sorted(records, key=lambda r: r["ts"])
    sessions, cur = [], [recs[0]]
    last = _parse_iso(recs[0]["ts"]) or datetime.min
    gap = timedelta(minutes=gap_minutes)
    for r in recs[1:]:
        t = _parse_iso(r["ts"]) or last
        if t - last > gap:
            sessions.append(cur)
            cur = [r]
        else:
            cur.append(r)
        last = t
    sessions.append(cur)
    out = []
    for s in sessions:
        out.append({
            "start": s[0]["ts"],
            "end": s[-1]["ts"],
            "count": len(s),
            "actors": sorted(Counter([r["actor_label"] for r in s]).items(), key=lambda x: -x[1]),
            "units": sorted(Counter([r["unit"] for r in s]).items(), key=lambda x: -x[1]),
        })
    return out

def _write_jsonl(path, records):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def _write_jsonl_gz(path, records):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def _chunk(records, chunk_size):
    for i in range(0, len(records), chunk_size):
        yield i // chunk_size, records[i:i+chunk_size]

def _compact(record, max_summary=160):
    out = {k: record.get(k, "") for k in ESSENTIAL_FIELDS}
    out["summary"] = (out["summary"] or "")[:max_summary]
    return out

# -------------- main API --------------

def export_changes(
    sources=None,
    jsonl_path=os.path.join(OUT_DIR, "ks_changes_all.jsonl"),
    compiled_path=os.path.join(OUT_DIR, "ks_changes_compiled.json"),
    gap_minutes=30,
    make_compact=True,
    compact_summary_chars=160,
    max_lines_per_chunk=2000
):
    """
    - Fetch records
    - Deduplicate by (ts, summary); prefer mentioned_unit/non-UNKNOWN
    - Backfill actor PIDs/labels
    - Write:
        * full JSONL
        * compiled JSON (with sessions, by-unit)
        * compact .jsonl.gz
        * chunked compact + prompt chunks
    """
    os.makedirs(OUT_DIR, exist_ok=True)

    raw = _fetch_changes_raw()
    # source filter is applied after normalization/dedup (we keep only those matching)
    deduped = _dedup_and_backfill(raw)
    if sources:
        srcset = set(sources)
        deduped = [r for r in deduped if (r.get("source") or "") in srcset]

    # --- FULL JSONL ---
    _write_jsonl(jsonl_path, deduped)

    # --- Aggregate ---
    by_unit = defaultdict(list)
    actor_counts = Counter()
    for r in deduped:
        by_unit[r["unit"]].append(r)
        actor_counts[r["actor_label"]] += 1

    units_summary = {}
    for unit, evs in by_unit.items():
        evs_sorted = sorted(evs, key=lambda x: x["ts"])
        units_summary[unit] = {
            "count": len(evs_sorted),
            "first": evs_sorted[0]["ts"] if evs_sorted else None,
            "last": evs_sorted[-1]["ts"] if evs_sorted else None,
            "actors": sorted(Counter([e["actor_label"] for e in evs_sorted]).items(), key=lambda x: -x[1]),
            "events": evs_sorted,
        }

    sessions = _sessionize(deduped, gap_minutes=gap_minutes)

    compiled = {
        "meta": {
            "source_filter": list(sources) if sources else "ALL",
            "total_changes": len(deduped),
            "actors": sorted(actor_counts.items(), key=lambda x: -x[1]),
            "time_range": {
                "start": deduped[0]["ts"] if deduped else None,
                "end": deduped[-1]["ts"] if deduped else None,
            },
            "session_gap_minutes": gap_minutes,
            "sessions": sessions,
        },
        "global_events": deduped,
        "units": units_summary
    }

    with open(compiled_path, "w", encoding="utf-8") as f:
        json.dump(compiled, f, indent=2, ensure_ascii=False)

    produced = [compiled_path, jsonl_path]

    # --- COMPACT exports (LLM-ready) ---
    if make_compact:
        compact = [{**_compact(r, max_summary=compact_summary_chars)} for r in deduped]
        compact_gz = os.path.join(OUT_DIR, "ks_changes_compact.jsonl.gz")
        _write_jsonl_gz(compact_gz, compact)
        produced.append(compact_gz)

        # chunked gz files
        chunks_dir = os.path.join(OUT_DIR, "ks_chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        idx = 1
        for _, batch in _chunk(compact, max_lines_per_chunk):
            p = os.path.join(chunks_dir, f"compact_chunk_{idx:04d}.jsonl.gz")
            _write_jsonl_gz(p, batch)
            produced.append(p)
            idx += 1

        # prompt-sized JSON bundles
        prompt_dir = os.path.join(OUT_DIR, "ks_prompt_chunks")
        os.makedirs(prompt_dir, exist_ok=True)
        meta = {
            "source_filter": list(sources) if sources else "ALL",
            "total_changes": len(deduped),
            "session_gap_minutes": gap_minutes,
            "hint": "Each file contains chronological, compact edits (ts, actor_label, unit, action, summary).",
        }
        idx = 1
        for _, batch in _chunk(compact, max_lines_per_chunk):
            prompt_json = {"meta": meta, "chunk_index": idx, "events": batch}
            p = os.path.join(prompt_dir, f"prompt_chunk_{idx:04d}.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(prompt_json, f, ensure_ascii=False)
            produced.append(p)
            idx += 1

    return produced
