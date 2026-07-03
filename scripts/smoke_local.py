"""本地联调冒烟：health → models → sessions → chat(SSE mock)。无需单独起 server。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.agent.console import answer, out, step, warn
from fastapi.testclient import TestClient

from server.main import app


def _parse_sse(raw: str) -> list[dict]:
    events: list[dict] = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


def run() -> int:
    step("本地联调冒烟", "TestClient 模拟完整 Web API 链路")
    errors = 0

    with TestClient(app) as client:
        # health
        r = client.get("/health")
        if r.status_code == 200 and r.json().get("status") == "ok":
            out("/health → ok", "后端健康检查通过")
        else:
            warn(str(r.status_code), "/health 异常")
            errors += 1

        # models
        r = client.get("/api/models?check_remote=false")
        if r.status_code == 200 and len(r.json().get("models", [])) >= 2:
            out(f"模型数 {len(r.json()['models'])}", "GET /api/models 正常")
        else:
            warn("models 响应异常", "检查 core/models")
            errors += 1

        # session + chat
        created = client.post(
            "/api/sessions",
            json={"user_id": "default", "title": "smoke", "model": "auto"},
        )
        if created.status_code != 200:
            warn("创建会话失败", created.text)
            errors += 1
            answer(f"冒烟未通过（{errors} 项）", "见上方提示")
            return 1

        session_id = created.json()["id"]
        mock_agent = MagicMock()
        mock_agent.session.messages = created.json()["messages"]

        def fake_chat(user_input: str, **kwargs) -> str:
            cb = kwargs.get("on_event")
            if cb:
                cb({"event": "assistant_reply", "content": "smoke ok"})
            return "smoke ok"

        mock_agent.chat.side_effect = fake_chat

        with patch("server.services.agent_service.CodingAgent", return_value=mock_agent):
            with client.stream(
                "POST",
                "/api/chat",
                json={
                    "user_id": "default",
                    "session_id": session_id,
                    "message": "ping",
                    "model": "auto",
                },
            ) as resp:
                body = resp.read().decode("utf-8") if resp.status_code == 200 else ""

        events = _parse_sse(body)
        if any(e.get("event") == "done" for e in events):
            out("SSE chat → done", "流式对话链路正常（Agent 已 Mock）")
        else:
            warn("未收到 done 事件", "检查 agent_service SSE")
            errors += 1

        client.delete(f"/api/sessions/{session_id}", params={"user_id": "default"})

    if errors:
        answer(f"冒烟未通过（{errors} 项）", "修复后重试")
        return 1

    answer(
        "本地联调冒烟通过",
        "可启动 uv run python -m server 与 cd apps/web && npm run dev 做浏览器验证",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
