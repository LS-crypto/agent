"""每用户独立数据库隔离测试。"""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from core.user.paths import user_db_path
from tests.conftest import auth_headers, register_user


def test_register_creates_per_user_database(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="isolated@example.com")
    user_id = auth["user"]["id"]

    db_file = user_db_path(user_id)
    assert db_file.is_file()

    conn = sqlite3.connect(db_file)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    assert "sessions" in tables


def test_users_have_separate_session_databases(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    alice = register_user(client, email="alice-db@example.com")
    bob = register_user(client, email="bob-db@example.com")

    alice_db = user_db_path(alice["user"]["id"])
    bob_db = user_db_path(bob["user"]["id"])
    assert alice_db != bob_db
    assert alice_db.is_file()
    assert bob_db.is_file()

    created = client.post(
        "/api/sessions",
        json={"title": "Alice private"},
        headers=auth_headers(alice["access_token"]),
    )
    assert created.status_code == 200

    conn = sqlite3.connect(alice_db)
    alice_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    conn.close()

    conn = sqlite3.connect(bob_db)
    bob_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    conn.close()

    assert alice_count == 1
    assert bob_count == 0

    bob_list = client.get(
        "/api/sessions",
        headers=auth_headers(bob["access_token"]),
    )
    assert bob_list.status_code == 200
    assert bob_list.json() == []
