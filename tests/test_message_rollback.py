"""撤回最后一轮对话测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from core.agent.multimodal import build_user_content
from server.repositories.sessions import SessionRepository
from tests.conftest import auth_headers, register_user


def test_rollback_last_turn_removes_user_and_assistant(client: TestClient) -> None:
    payload = register_user(client, email="rollback-user@example.com")
    headers = auth_headers(payload["access_token"])

    created = client.post(
        "/api/sessions",
        json={"title": "新会话"},
        headers=headers,
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    repo = SessionRepository()
    user_id = payload["user"]["id"]
    repo.append_user_message(session_id, user_id, "第一条")
    repo.update_messages(
        session_id,
        user_id,
        repo.get(session_id, user_id)["messages"]
        + [
            {"role": "assistant", "content": "回复一"},
            {"role": "user", "content": "第二条"},
            {"role": "assistant", "content": "回复二"},
        ],
    )

    res = client.post(
        f"/api/sessions/{session_id}/rollback-last-turn",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["message"] == "第二条"
    assert body["images"] == []

    messages = body["session"]["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant"]
    assert messages[-2]["content"] == "第一条"
    assert messages[-1]["content"] == "回复一"

    repo.delete(session_id, user_id)


def test_rollback_last_turn_with_tool_chain(client: TestClient) -> None:
    payload = register_user(client, email="rollback-tools@example.com")
    headers = auth_headers(payload["access_token"])

    created = client.post(
        "/api/sessions",
        json={"title": "新会话"},
        headers=headers,
    )
    session_id = created.json()["id"]
    user_id = payload["user"]["id"]
    repo = SessionRepository()

    repo.append_user_message(session_id, user_id, "写文件")
    repo.update_messages(
        session_id,
        user_id,
        repo.get(session_id, user_id)["messages"]
        + [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "write_file", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "ok"},
            {"role": "assistant", "content": "已写入"},
        ],
    )

    res = client.post(
        f"/api/sessions/{session_id}/rollback-last-turn",
        headers=headers,
    )
    assert res.status_code == 200
    roles = [m["role"] for m in res.json()["session"]["messages"]]
    assert roles == ["system"]

    repo.delete(session_id, user_id)


def test_rollback_last_turn_multimodal(client: TestClient) -> None:
    payload = register_user(client, email="rollback-vl@example.com")
    headers = auth_headers(payload["access_token"])

    created = client.post("/api/sessions", json={"title": "新会话"}, headers=headers)
    session_id = created.json()["id"]
    user_id = payload["user"]["id"]
    repo = SessionRepository()

    png = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    content = build_user_content("看图", [png])
    repo.append_user_message(session_id, user_id, content)
    repo.update_messages(
        session_id,
        user_id,
        repo.get(session_id, user_id)["messages"]
        + [{"role": "assistant", "content": "这是一张图"}],
    )

    res = client.post(
        f"/api/sessions/{session_id}/rollback-last-turn",
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["message"] == "看图"
    assert len(body["images"]) == 1
    assert body["images"][0].startswith("data:image/png;base64,")

    repo.delete(session_id, user_id)


def test_rollback_without_user_message_400(client: TestClient) -> None:
    payload = register_user(client, email="rollback-empty@example.com")
    headers = auth_headers(payload["access_token"])

    created = client.post("/api/sessions", json={"title": "新会话"}, headers=headers)
    session_id = created.json()["id"]

    res = client.post(
        f"/api/sessions/{session_id}/rollback-last-turn",
        headers=headers,
    )
    assert res.status_code == 400

    SessionRepository().delete(session_id, payload["user"]["id"])
