"""主管后台 API 与活动测试。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, make_admin, register_user, save_user_api_key


def test_non_admin_cannot_list_users(client: TestClient) -> None:
    auth = register_user(client, email="not-admin@example.com")
    res = client.get("/api/admin/users", headers=auth_headers(auth["access_token"]))
    assert res.status_code == 403


def test_register_creates_admin_mirror_file(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="mirror@example.com")
    user_id = auth["user"]["id"]
    user_file = runtime / "admin" / "users" / f"{user_id}.json"
    index_file = runtime / "admin" / "users" / "index.json"

    assert user_file.is_file()
    assert index_file.is_file()
    body = user_file.read_text(encoding="utf-8")
    assert "mirror@example.com" in body
    assert "sk-" not in body


def test_admin_lists_users_without_api_key_hints(
    client: TestClient, db_path, tmp_path, monkeypatch
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    user_auth = register_user(client, email="regular@example.com")
    save_user_api_key(client, user_auth["access_token"], "sk-usersecret1234567890")

    admin_auth = register_user(client, email="boss@example.com")
    make_admin(db_path, admin_auth["user"]["id"])

    res = client.get(
        "/api/admin/users",
        headers=auth_headers(admin_auth["access_token"]),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 2
    blob = json.dumps(body)
    assert "sk-usersecret" not in blob
    assert "***" not in blob

    regular = next(u for u in body["users"] if u["email"] == "regular@example.com")
    assert regular["has_api_key"] is True
    assert "hint" not in regular


def test_admin_activity_records_user_questions(
    client: TestClient, db_path, tmp_path, monkeypatch
) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    from core.agent.activity import ActivityLogger

    user_auth = register_user(client, email="asker@example.com")
    logger = ActivityLogger(user_auth["user"]["id"])
    logger.user_message("如何用 Python 写 hello world？")

    admin_auth = register_user(client, email="admin2@example.com")
    make_admin(db_path, admin_auth["user"]["id"])

    res = client.get(
        "/api/admin/activity",
        headers=auth_headers(admin_auth["access_token"]),
    )
    assert res.status_code == 200
    events = res.json()["events"]
    assert any("hello world" in (e.get("content") or "") for e in events)


def test_admin_user_detail_shows_recent_questions(
    client: TestClient, db_path, tmp_path, monkeypatch
) -> None:
    runtime = tmp_path / "runtime"
    date_str = datetime.now().strftime("%Y-%m-%d")
    logs = runtime / "logs" / date_str
    logs.mkdir(parents=True)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    user_auth = register_user(client, email="detail@example.com")
    user_id = user_auth["user"]["id"]
    log_path = logs / f"{user_id}.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "time": f"{date_str}T11:00:00",
                "user_id": user_id,
                "event": "user_message",
                "content": "测试问题 A",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    admin_auth = register_user(client, email="admin3@example.com")
    make_admin(db_path, admin_auth["user"]["id"])

    res = client.get(
        f"/api/admin/users/{user_id}",
        headers=auth_headers(admin_auth["access_token"]),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["recent_questions"][0]["content"] == "测试问题 A"
    assert "sk-" not in json.dumps(body)


def test_reject_non_dashscope_api_key_format(client: TestClient) -> None:
    auth = register_user(client, email="bad-key@example.com")
    res = client.put(
        "/api/settings/api-key",
        json={"api_key": "not-a-valid-key"},
        headers=auth_headers(auth["access_token"]),
    )
    assert res.status_code == 400
    assert "sk-" in res.json()["detail"]
