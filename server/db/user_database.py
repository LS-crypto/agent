"""每用户独立 SQLite（会话数据）。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from core.user.paths import user_db_path

_USER_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '新会话',
    messages_json TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'auto',
    permission_level TEXT NOT NULL DEFAULT 'balanced',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
"""


def init_user_db(user_id: str) -> None:
    """初始化用户专属会话库。"""
    path = user_db_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(_USER_SESSIONS_SCHEMA)


def user_db_exists(user_id: str) -> bool:
    return user_db_path(user_id).is_file()


@contextmanager
def get_user_connection(user_id: str) -> Iterator[sqlite3.Connection]:
    path = user_db_path(user_id)
    if not path.is_file():
        init_user_db(user_id)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
