import sqlite3
from pathlib import Path
from contextlib import contextmanager
from .config import get_settings

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS devices (
 id TEXT PRIMARY KEY, label TEXT NOT NULL, token_hash TEXT NOT NULL,
 created_at TEXT NOT NULL, last_seen TEXT, revoked_at TEXT, metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS enrollments (
 code_hash TEXT PRIMARY KEY, label TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, device_id TEXT NOT NULL, operation TEXT NOT NULL,
 arguments_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL,
 created_at TEXT NOT NULL, leased_at TEXT, finished_at TEXT,
 result_json TEXT, error TEXT,
 FOREIGN KEY(device_id) REFERENCES devices(id)
);
CREATE INDEX IF NOT EXISTS jobs_device_status ON jobs(device_id, status, created_at);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL,
 action TEXT NOT NULL, target TEXT, details_json TEXT NOT NULL DEFAULT '{}'
);
"""

def connect():
    path = Path(get_settings().bridge_database)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)

@contextmanager
def transaction():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
