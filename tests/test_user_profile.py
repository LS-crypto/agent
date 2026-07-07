"""用户资料与管理员引导测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from server.services.admin_bootstrap import ensure_admin_account
from tests.conftest import auth_headers, register_user


def test_update_profile_display_name_and_avatar(client: TestClient) -> None:
    auth = register_user(client, email="profile@example.com")
    headers = auth_headers(auth["access_token"])

    res = client.patch(
        "/api/settings/profile",
        json={"display_name": "小明", "avatar": "🐱"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["display_name"] == "小明"
    assert body["avatar"] == "🐱"

    me = client.get("/api/settings/profile", headers=headers)
    assert me.status_code == 200
    assert me.json()["display_name"] == "小明"


def test_ensure_admin_account_creates_admin(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass123")

    ensure_admin_account()

    login = client.post(
        "/api/auth/login",
        json={"email": "boss@example.com", "password": "adminpass123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "admin"
