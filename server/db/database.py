"""SQLite 连接与 schema（全局认证库）。"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from core.user.paths import legacy_runtime_db_path, runtime_db_path

_AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    last_login_at TEXT
);
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


def _resolve_auth_db_path() -> Path:
    path = runtime_db_path()
    legacy = legacy_runtime_db_path()
    if not path.is_file() and legacy.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, path)
    return path


def init_db() -> None:
    path = _resolve_auth_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_AUTH_SCHEMA)
        _migrate(conn)
        _migrate_sessions_to_per_user(conn)


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

    user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "display_name" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    if "avatar" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN avatar TEXT")

    session_cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    if session_cols:
        _ensure_legacy_default_user(conn)


def _migrate_sessions_to_per_user(conn: sqlite3.Connection) -> None:
    """将旧版中央库中的会话迁移到每用户独立库。"""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchall()
    }
    if "sessions" not in tables:
        return

    rows = conn.execute(
        """
        SELECT id, user_id, title, messages_json, created_at, updated_at,
               COALESCE(model, 'auto') AS model,
               COALESCE(permission_level, 'balanced') AS permission_level
        FROM sessions
        """
    ).fetchall()
    if not rows:
        conn.execute("DROP TABLE IF EXISTS sessions")
        return

    from server.db.user_database import get_user_connection, init_user_db
    from server.services.user_provision import provision_user_storage

    for row in rows:
        data = dict(row)
        user_id = data["user_id"]
        provision_user_storage(user_id)
        init_user_db(user_id)
        with get_user_connection(user_id) as uconn:
            uconn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    id, user_id, title, messages_json, model, permission_level,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["id"],
                    user_id,
                    data["title"],
                    data["messages_json"],
                    data["model"],
                    data["permission_level"],
                    data["created_at"],
                    data["updated_at"],
                ),
            )

    conn.execute("DROP TABLE IF EXISTS sessions")
    conn.execute("DROP INDEX IF EXISTS idx_sessions_user_id")


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
    path = _resolve_auth_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
