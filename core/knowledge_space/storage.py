import sqlite3, os, json, uuid
from datetime import datetime
import hashlib

# All KS data under this directory
KS_DIR = "data/knowledge_space"
DB_PATH = os.path.join(KS_DIR, "knowledge_space.db")

DDL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS collections(
  id TEXT PRIMARY KEY,
  root_path TEXT UNIQUE,
  label TEXT,
  created_at TEXT,
  last_scan TEXT,
  total_files INTEGER,
  total_bytes INTEGER
);

CREATE TABLE IF NOT EXISTS artifacts(
  id TEXT PRIMARY KEY,              -- stable hash of collection_id + relative_path
  path TEXT,                        -- relative_path within the collection
  type TEXT, title TEXT, created_at TEXT
);

CREATE TABLE IF NOT EXISTS versions(
  id TEXT PRIMARY KEY, artifact_id TEXT, hash TEXT, parent_version_id TEXT,
  created_at TEXT, author TEXT
);

CREATE TABLE IF NOT EXISTS events(
  id TEXT PRIMARY KEY, source TEXT, event_type TEXT, artifact_id TEXT,
  version_id TEXT, actor TEXT, ts TEXT, raw TEXT
);

CREATE TABLE IF NOT EXISTS deltas(
  id TEXT PRIMARY KEY, version_id TEXT, kind TEXT, summary TEXT, payload_json TEXT
);
"""

def get_conn(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(DDL)
    return conn

def insert(table: str, row: dict, db_path: str = DB_PATH):
    conn = get_conn(db_path)
    cols = ",".join(row.keys())
    qs   = ",".join(["?"]*len(row))
    vals = [json.dumps(v) if isinstance(v,(dict,list)) else v for v in row.values()]
    conn.execute(f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({qs})", vals)
    conn.commit(); conn.close()

# ---------- Collections & stable keys ----------

def _abs(p: str) -> str:
    return os.path.abspath(os.path.normpath(p))

def get_or_create_collection(root_path: str):
    """Return (collection_id, label) for a given root folder path."""
    root_abs = _abs(root_path)
    label = os.path.basename(root_abs)
    conn = get_conn(); c = conn.cursor()
    row = c.execute("SELECT id, label FROM collections WHERE root_path=?", (root_abs,)).fetchone()
    if row:
        coll_id, label_db = row
        conn.close()
        return coll_id, (label_db or label)
    # create
    coll_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    c.execute(
        "INSERT INTO collections(id, root_path, label, created_at, last_scan, total_files, total_bytes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (coll_id, root_abs, label, now, None, 0, 0)
    )
    conn.commit(); conn.close()
    return coll_id, label

def update_collection_scan(collection_id: str, total_files: int, total_bytes: int):
    conn = get_conn(); c = conn.cursor()
    c.execute(
        "UPDATE collections SET last_scan=?, total_files=?, total_bytes=? WHERE id=?",
        (datetime.utcnow().isoformat(), total_files, total_bytes, collection_id)
    )
    conn.commit(); conn.close()

def make_stable_artifact_id(collection_id: str, relative_path: str) -> str:
    """Stable within a collection even if the folder is moved on disk."""
    key = f"{collection_id}:{relative_path.replace(os.sep,'/')}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()
