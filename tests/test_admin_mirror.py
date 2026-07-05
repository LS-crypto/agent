"""主管后台 API 测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user


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
