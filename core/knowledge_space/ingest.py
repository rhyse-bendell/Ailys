# core/knowledge_space/ingest.py
import os, uuid
from datetime import datetime
from difflib import unified_diff
from memory.memory import save_memory_event

from .storage import (
    insert, KS_DIR, get_or_create_collection,
    update_collection_scan, make_stable_artifact_id
)
from .sniffers import (
    looks_like_changelog_filename, extract_changelog_rows, is_textlike,
    detect_activity_log, parse_changelog_row,
    detect_bracketed_activity_log, parse_bracketed_activity_row   # NEW
)
from .participants import get_or_create_pid  # auto PID

SNAP_DIR = os.path.join(KS_DIR, "snapshots")
os.makedirs(SNAP_DIR, exist_ok=True)

def _snap_path(collection_id: str, rel_path: str) -> str:
    import hashlib
    base = hashlib.md5(f"{collection_id}:{rel_path}".encode("utf-8")).hexdigest()
    return os.path.join(SNAP_DIR, base + ".txt")

def _load_snapshot(collection_id: str, rel_path: str):
    fp = _snap_path(collection_id, rel_path)
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return None

def _save_snapshot(collection_id: str, rel_path: str, text: str):
    fp = _snap_path(collection_id, rel_path)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(text or "")

def _read_text(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def _derive_unit_from_changelog_filename(fn: str) -> str:
    # e.g., "Activity 4 Template_changelog.txt" -> "Activity 4 Template"
    name, _ext = os.path.splitext(fn)
    for suffix in ("_changelog", "-changelog", ".changelog", "_activity", "-activity"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)].strip()
    return name

def review_folder(root_path: str, actor_hint: str|None=None, mode: str = "auto") -> dict:
    """
    mode:
      - "auto": parse change logs + compute file diffs
      - "log_only": only parse change logs (downloaded/archive spaces)
    """
    collection_id, label = get_or_create_collection(root_path)
    files_seen = edits = logs_parsed = 0
    total_bytes = 0
    now_iso = datetime.utcnow().isoformat()

    for dirpath, _, filenames in os.walk(root_path):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if not is_textlike(full):
                continue

            rel_path = os.path.relpath(full, root_path).replace(os.sep, "/")
            files_seen += 1
            try:
                total_bytes += os.path.getsize(full)
            except Exception:
                pass

            text = _read_text(full)

            # ---------- CHANGELOG-LIKE FILES ----------
            if looks_like_changelog_filename(fn) or detect_activity_log(text) or detect_bracketed_activity_log(text):  # NEW
                rows = extract_changelog_rows(text)
                # default year guess: file modified year (helps year-less human times)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(full))
                    default_year = mtime.year
                except Exception:
                    default_year = None

                for row in rows[:5000]:
                    # Try new bracketed parser first
                    parsed = parse_bracketed_activity_row(row, default_year=default_year)
                    delta_kind = "log_content"
                    if not parsed:
                        parsed = parse_changelog_row(row) or {}
                        delta_kind = "log_entry"

                    ver_id = str(uuid.uuid4())
                    art_id = make_stable_artifact_id(collection_id, rel_path)

                    ts_iso = (parsed.get("ts") or datetime.utcnow()).isoformat()
                    actor  = parsed.get("actor") or actor_hint or ""

                    if actor:
                        try:
                            get_or_create_pid(actor, first_seen_ts=ts_iso)
                        except Exception:
                            pass

                    # mentioned unit (prefer parser value; else derive from filename)
                    mentioned_unit = parsed.get("unit")
                    if not mentioned_unit:
                        mentioned_unit = _derive_unit_from_changelog_filename(fn)

                    payload = {
                        "root_label": label,
                        "rel_path": rel_path,
                        "path": full,
                        "row": row,
                        "action": parsed.get("action") or "",
                        "mentioned_unit": mentioned_unit
                    }
                    extras = parsed.get("extras") or {}
                    if "content" in extras:
                        payload["content"] = extras["content"]

                    insert("events", {
                        "id": str(uuid.uuid4()), "source":"changelog", "event_type":"edited",
                        "artifact_id": art_id, "version_id": ver_id,
                        "actor": actor, "ts": ts_iso, "raw": row
                    })
                    insert("deltas", {
                        "id": str(uuid.uuid4()), "version_id": ver_id, "kind": delta_kind,
                        "summary": (parsed.get("summary") or row)[:500],
                        "payload_json": payload
                    })
                    save_memory_event(
                        event_type="ks_log_entry",
                        source_text=row[:1000],
                        ai_insight=f"[{label}] Log row in {rel_path}",
                        user_input="Knowledge Space Review",
                        tags=["knowledge_space","changelog","timeline"],
                        file_path=full
                    )
                    logs_parsed += 1

            # ---------- FILE DIFFS ----------
            if mode == "log_only":
                continue

            prev = _load_snapshot(collection_id, rel_path)
            if prev is None:
                ver_id = str(uuid.uuid4())
                art_id = make_stable_artifact_id(collection_id, rel_path)
                insert("events", {
                    "id": str(uuid.uuid4()), "source":"filesystem", "event_type":"created",
                    "artifact_id": art_id, "version_id": ver_id,
                    "actor": actor_hint or "", "ts": now_iso, "raw": "{}"
                })
                _save_snapshot(collection_id, rel_path, text)
                continue

            if prev != text:
                diff = list(unified_diff(prev.splitlines(), text.splitlines(), lineterm=""))
                adds = sum(l.startswith('+') for l in diff)
                dels = sum(l.startswith('-') for l in diff)
                ver_id = str(uuid.uuid4())
                art_id = make_stable_artifact_id(collection_id, rel_path)
                insert("events", {
                    "id": str(uuid.uuid4()), "source":"filesystem", "event_type":"edited",
                    "artifact_id": art_id, "version_id": ver_id,
                    "actor": actor_hint or "", "ts": now_iso, "raw": "{}"
                })
                insert("deltas", {
                    "id": str(uuid.uuid4()), "version_id": ver_id, "kind":"text_edit",
                    "summary": f"+{adds} / -{dels}",
                    "payload_json": {"root_label": label, "rel_path": rel_path, "path": full, "diff": diff[:2000]}
                })
                _save_snapshot(collection_id, rel_path, text)
                edits += 1

                save_memory_event(
                    event_type="ks_file_delta",
                    source_text="\n".join(diff[:80]),
                    ai_insight=f"[{label}] Edited {rel_path} (+{adds}/-{dels})",
                    user_input="Knowledge Space Review",
                    tags=["knowledge_space","delta","timeline"],
                    file_path=full
                )

    update_collection_scan(collection_id, total_files=files_seen, total_bytes=total_bytes)
    save_memory_event(
        event_type="ks_review_summary",
        source_text=f"Collection: {label}\nRoot: {root_path}\nFiles seen: {files_seen}\nEdits: {edits}\nLog rows: {logs_parsed}",
        ai_insight=f"[{label}] Knowledge Space review completed.",
        user_input="Knowledge Space Review",
        tags=["knowledge_space","summary","timeline"],
        file_path=root_path
    )
    return {"files_seen": files_seen, "edits": edits, "log_rows": logs_parsed}
