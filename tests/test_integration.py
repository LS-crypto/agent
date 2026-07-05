"""集成测试：HTTP /health、SSE 流式对话（Mock Agent，不调百炼）。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user, save_user_api_key


def _parse_sse_events(raw: str) -> list[dict]:
    events: list[dict] = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_sse_chat_stream_mock(client: TestClient) -> None:
    """POST /api/chat 应返回 SSE，含 done 事件（Agent 已 Mock）。"""
    auth = register_user(client)
    headers = auth_headers(auth["access_token"])
    save_user_api_key(client, auth["access_token"])

    created = client.post(
        "/api/sessions",
        json={"title": "集成测试", "model": "qwen3.6-flash"},
        headers=headers,
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    mock_agent = MagicMock()
    mock_agent.session.messages = created.json()["messages"]

    def fake_chat(user_input: str, **kwargs) -> str:
        on_event = kwargs.get("on_event")
        if on_event:
            on_event({"event": "loop_round", "round": 1, "tool_count": 3})
            on_event({"event": "assistant_reply", "content": "集成测试回复"})
        mock_agent.session.messages = [
            *mock_agent.session.messages,
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": "集成测试回复"},
        ]
        return "集成测试回复"

    mock_agent.chat.side_effect = fake_chat

    with patch(
        "server.services.agent_service.CodingAgent",
        return_value=mock_agent,
    ):
        with client.stream(
            "POST",
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "你好",
                "model": "qwen3.6-flash",
            },
            headers=headers,
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            body = resp.read().decode("utf-8")

    detail = client.get(f"/api/sessions/{session_id}", headers=headers)
    assert detail.status_code == 200
    msgs = detail.json()["messages"]
    assert any(m.get("role") == "user" and m.get("content") == "你好" for m in msgs)

    events = _parse_sse_events(body)
    event_names = [e.get("event") for e in events]
    assert "loop_round" in event_names
    assert "assistant_reply" in event_names
    assert "done" in event_names
    done = next(e for e in events if e.get("event") == "done")
    assert done.get("content") == "集成测试回复"

    client.delete(f"/api/sessions/{session_id}", headers=headers)
