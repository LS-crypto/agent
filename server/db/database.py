"""SQLite 连接与 schema。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from core.user.paths import runtime_db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '新会话',
    messages_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE TABLE IF NOT EXISTS user_secrets (
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'dashscope',
    ciphertext TEXT NOT NULL,
    key_version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, provider),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def init_db() -> None:
    path = runtime_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")

    user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if not user_cols:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                last_login_at TEXT
            );
            """
        )

    cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "model" not in cols:
        conn.execute(
            "ALTER TABLE sessions ADD COLUMN model TEXT NOT NULL DEFAULT 'auto'"
        )
    if "permission_level" not in cols:
        conn.execute(
            "ALTER TABLE sessions ADD COLUMN permission_level TEXT NOT NULL DEFAULT 'balanced'"
        )

    secret_cols = {row[1] for row in conn.execute("PRAGMA table_info(user_secrets)")}
    if not secret_cols:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_secrets (
                user_id TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'dashscope',
                ciphertext TEXT NOT NULL,
                key_version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, provider),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )

    _ensure_legacy_default_user(conn)


def _ensure_legacy_default_user(conn: sqlite3.Connection) -> None:
    """为升级前 default 会话保留占位用户，避免外键失败。"""
    orphan = conn.execute(
        "SELECT 1 FROM sessions WHERE user_id = 'default' LIMIT 1"
    ).fetchone()
    if orphan is None:
        return
    exists = conn.execute(
        "SELECT 1 FROM users WHERE id = 'default' LIMIT 1"
    ).fetchone()
    if exists is not None:
        return
    conn.execute(
        """
        INSERT INTO users (
            id, email, password_hash, role, status, created_at, last_login_at
        )
        VALUES ('default', 'legacy-default@local', '', 'admin', 'active', datetime('now'), NULL)
        """
    )


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    path = runtime_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
