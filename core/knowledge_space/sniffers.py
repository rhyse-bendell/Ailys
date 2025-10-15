# core/knowledge_space/sniffers.py
import os
import re
from datetime import datetime

# ---------------------------
# Simple text detection
# ---------------------------

TEXT_EXT = {
    ".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml", ".xml",
    ".ini", ".cfg", ".conf", ".log"
}

def is_textlike(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if ext in TEXT_EXT:
        return True
    try:
        return os.path.getsize(path) < 5_000_000  # 5MB
    except Exception:
        return False

# ---------------------------
# Change-log filename heuristic
# ---------------------------

CHANGELOG_HINTS = [
    "changelog", "change_log", "change-log", "history", "audit",
    "activity", "revisions", "revision", "rev_history", "log", "trail"
]

def looks_like_changelog_filename(fn: str) -> bool:
    f = fn.lower()
    return any(h in f for h in CHANGELOG_HINTS)

def extract_changelog_rows(text: str):
    if not text:
        return []
    return [ln.strip("\ufeff ").rstrip() for ln in text.splitlines() if ln.strip()]

# ---------------------------
# Robust detector + parser for Drive-like audit rows
# ---------------------------

ISOZ = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z"
PEOPLE = r"people/\d{6,}"
ACTION = r"(created|edited|moved|renamed|deleted)"

_MOVED = re.compile(
    rf"^\s*(?P<ts>{ISOZ})\s*-\s*(?P<actor>{PEOPLE})\s+"
    rf"moved\s+(?P<name>.+?)\s+from\s+(?P<from>.+?)\s+to\s+(?P<to>.+?)\s*$",
    re.IGNORECASE
)

_RENAMED = re.compile(
    rf"^\s*(?P<ts>{ISOZ})\s*-\s*(?P<actor>{PEOPLE})\s+"
    rf"renamed\s+(?P<old>.+?)\s+to\s+(?P<new>.+?)\s+at\s+(?P<path>.+?)\s*$",
    re.IGNORECASE
)

_ACTION_AT = re.compile(
    rf"^\s*(?P<ts>{ISOZ})\s*-\s*(?P<actor>{PEOPLE})\s+"
    rf"(?P<action>{ACTION})\s+(?P<name>.+?)\s+at\s+(?P<path>.+?)\s*$",
    re.IGNORECASE
)

_FALLBACK_DATES = [
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
    "%d-%b-%Y %H:%M", "%d-%b-%Y",
]

def _parse_isoz(tsz: str):
    try:
        return datetime.fromisoformat(tsz.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None

def detect_activity_log(text: str) -> bool:
    if not text:
        return False
    cnt = 0
    for ln in text.splitlines()[:200]:
        if _MOVED.search(ln) or _RENAMED.search(ln) or _ACTION_AT.search(ln):
            cnt += 1
    return cnt >= 3

def parse_changelog_row(row: str):
    """
    Return: {ts, actor, unit, summary, action, extras: {...}}
    - actor is the raw 'people/<id>' when present (never blank if present in the row)
    - unit is the mentioned target (actual file/folder affected)
    """
    s = row.strip()

    m = _MOVED.search(s)
    if m:
        return {
            "ts": _parse_isoz(m.group("ts")),
            "actor": m.group("actor"),
            "unit": m.group("to").strip(),
            "summary": s,
            "action": "moved",
            "extras": {"name": m.group("name"), "from": m.group("from"), "to": m.group("to")}
        }

    m = _RENAMED.search(s)
    if m:
        return {
            "ts": _parse_isoz(m.group("ts")),
            "actor": m.group("actor"),
            "unit": m.group("path").strip(),
            "summary": s,
            "action": "renamed",
            "extras": {"old": m.group("old"), "new": m.group("new")}
        }

    m = _ACTION_AT.search(s)
    if m:
        return {
            "ts": _parse_isoz(m.group("ts")),
            "actor": m.group("actor"),
            "unit": m.group("path").strip(),
            "summary": s,
            "action": m.group("action").lower(),
            "extras": {"name": m.group("name")}
        }

    # fallback (notes-style rows with only a date string)
    dt = None
    for fmt in _FALLBACK_DATES:
        try:
            dt = datetime.strptime(s, fmt)
            break
        except Exception:
            pass
    return {"ts": dt, "actor": None, "unit": None, "summary": s, "action": "note", "extras": {}}

# --------------------------------------------------------------------
# NEW: Bracketed "activity" logs with inline content (e.g., "[EDIT] Name (• 2:14 PM, Aug 19 (MDT)): text")
# --------------------------------------------------------------------

# Example row:
# [EDIT] Ames Samavatekbatan (• 2:14 PM, Aug 19 (MDT)): Creating a supportive environment ...
_BRACKETED = re.compile(
    r"^\s*\[(?P<action>EDIT|DELETE|CREATED|CREATE|ADDED|REMOVED)\]\s*"
    r"(?P<actor>[^(\]]+?)\s*\(\s*•\s*(?P<when>[^)]+)\)\s*:\s*(?P<content>.+?)\s*$",
    re.IGNORECASE
)

# Try several human-friendly time formats found in these logs (yearless; we will backfill year upstream if needed)
_HUMAN_TIME_FMTS = [
    "%I:%M %p, %b %d (%Z)",    # 2:14 PM, Aug 19 (MDT)
    "%I:%M %p, %b %d",         # 2:14 PM, Aug 19
    "%H:%M, %b %d (%Z)",       # 14:14, Aug 19 (MDT)
    "%H:%M, %b %d",            # 14:14, Aug 19
]

def detect_bracketed_activity_log(text: str) -> bool:
    if not text:
        return False
    hits = 0
    for ln in text.splitlines()[:200]:
        if _BRACKETED.search(ln):
            hits += 1
    return hits >= 2

def parse_bracketed_activity_row(row: str, default_year: int | None = None):
    """
    Parse "[EDIT] Name (• 2:14 PM, Aug 19 (MDT)): <content>"
    Returns: {ts, actor, unit: None, summary, action, extras:{content:str}}
    - 'unit' will usually be derived from filename in ingest (e.g., stem of "..._changelog.txt")
    - ts will try to parse time-of-day & month/day; if year is missing, default_year can be injected by caller
    """
    s = row.strip()
    m = _BRACKETED.search(s)
    if not m:
        return None
    action = m.group("action").lower()
    actor  = m.group("actor").strip()
    when   = m.group("when").strip()
    content = m.group("content").strip()

    ts = None
    for fmt in _HUMAN_TIME_FMTS:
        try:
            # Parse without year; inject year if provided
            dt = datetime.strptime(when, fmt)
            if default_year is not None:
                dt = dt.replace(year=default_year)
            ts = dt
            break
        except Exception:
            continue

    return {
        "ts": ts,
        "actor": actor,
        "unit": None,                # let ingest derive from filename if needed
        "summary": content[:500],
        "action": action,
        "extras": {"content": content}
    }
