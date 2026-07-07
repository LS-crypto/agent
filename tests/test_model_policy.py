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


def test_user_models_include_third_party_and_vision(client: TestClient) -> None:
    auth = register_user(client, email="models-user@example.com")
    headers = auth_headers(auth["access_token"])
    res = client.get("/api/models?check_remote=false", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body.get("role_restricted") is True
    ids = {m["id"] for m in body["models"]}
    assert "auto" not in ids
    for mid in (
        "qwen3.6-flash",
        "qwen3.7-plus",
        "deepseek-v4-pro",
        "glm-5.2",
        "qwen3-vl-plus",
    ):
        assert mid in ids, mid


def test_user_can_select_deepseek_model(client: TestClient) -> None:
    auth = register_user(client, email="deepseek-user@example.com")
    headers = auth_headers(auth["access_token"])
    created = client.post(
        "/api/sessions",
        json={"title": "ds", "model": "deepseek-v4-pro"},
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["model"] == "deepseek-v4-pro"
