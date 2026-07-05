"""J0 鉴权与用户隔离测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user


def test_unauthenticated_sessions_401(client: TestClient) -> None:
    res = client.get("/api/sessions")
    assert res.status_code == 401


def test_register_login_me(client: TestClient) -> None:
    payload = register_user(client, email="alice@example.com")
    headers = auth_headers(payload["access_token"])

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    login = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "testpass123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "alice@example.com"


def test_user_cannot_access_other_session(client: TestClient) -> None:
    alice = register_user(client, email="alice-isolation@example.com")
    bob = register_user(client, email="bob-isolation@example.com")

    created = client.post(
        "/api/sessions",
        json={"title": "Alice only"},
        headers=auth_headers(alice["access_token"]),
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    denied = client.get(
        f"/api/sessions/{session_id}",
        headers=auth_headers(bob["access_token"]),
    )
    assert denied.status_code == 404


def test_duplicate_email_rejected(client: TestClient) -> None:
    register_user(client, email="dup@example.com")
    res = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "testpass123"},
    )
    assert res.status_code == 400
