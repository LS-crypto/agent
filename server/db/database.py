"""SQLite 连接与 schema。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from core.user.paths import runtime_db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '新会话',
    messages_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
"""


def init_db() -> None:
    path = runtime_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "model" not in cols:
        conn.execute(
            "ALTER TABLE sessions ADD COLUMN model TEXT NOT NULL DEFAULT 'auto'"
        )
    if "permission_level" not in cols:
        conn.execute(
            "ALTER TABLE sessions ADD COLUMN permission_level TEXT NOT NULL DEFAULT 'balanced'"
        )


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    path = runtime_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
