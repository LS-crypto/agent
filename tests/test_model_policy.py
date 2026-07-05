"""J2 模型权限测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user, save_user_api_key


def test_user_cannot_create_session_with_auto(client: TestClient) -> None:
    auth = register_user(client, email="auto-deny@example.com")
    headers = auth_headers(auth["access_token"])
    res = client.post(
        "/api/sessions",
        json={"title": "auto", "model": "auto"},
        headers=headers,
    )
    assert res.status_code == 403


def test_user_cannot_chat_with_auto_model(client: TestClient) -> None:
    auth = register_user(client, email="chat-auto@example.com")
    headers = auth_headers(auth["access_token"])
    save_user_api_key(client, auth["access_token"])

    created = client.post(
        "/api/sessions",
        json={"title": "x", "model": "qwen3.6-flash"},
        headers=headers,
    )
    session_id = created.json()["id"]

    res = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "hi", "model": "auto"},
        headers=headers,
    )
    assert res.status_code == 403
