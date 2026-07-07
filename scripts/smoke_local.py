"""本地联调冒烟：health → models → sessions → chat(SSE mock)。无需单独起 server。"""

from __future__ import annotations

import json
import os
import sys
import uuid
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

        # auth（models / sessions 均需登录）
        smoke_email = f"smoke-{uuid.uuid4().hex[:8]}@local.test"
        reg = client.post(
            "/api/auth/register",
            json={"email": smoke_email, "password": "smokepass123"},
        )
        if reg.status_code != 201:
            warn("注册失败", reg.text)
            errors += 1
            answer(f"冒烟未通过（{errors} 项）", "见上方提示")
            return 1
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        smoke_model = "qwen3.7-plus"

        # models
        r = client.get("/api/models?check_remote=false", headers=headers)
        if r.status_code == 200 and len(r.json().get("models", [])) >= 2:
            out(f"模型数 {len(r.json()['models'])}", "GET /api/models 正常")
        else:
            warn("models 响应异常", "检查 core/models")
            errors += 1

        created = client.post(
            "/api/sessions",
            json={"title": "smoke", "model": smoke_model},
            headers=headers,
        )
        if created.status_code != 200:
            warn("创建会话失败", created.text)
            errors += 1
            answer(f"冒烟未通过（{errors} 项）", "见上方提示")
            return 1

        session_id = created.json()["id"]

        dash_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not dash_key:
            warn("未配置 DASHSCOPE_API_KEY", "跳过 chat 链路；请在 .env 填入密钥")
            errors += 1
            client.delete(f"/api/sessions/{session_id}", headers=headers)
            answer(f"冒烟未通过（{errors} 项）", "见上方提示")
            return 1

        key_res = client.put(
            "/api/settings/api-key",
            json={"api_key": dash_key},
            headers=headers,
        )
        if key_res.status_code != 200:
            warn("保存用户 API Key 失败", key_res.text)
            errors += 1
            client.delete(f"/api/sessions/{session_id}", headers=headers)
            answer(f"冒烟未通过（{errors} 项）", "见上方提示")
            return 1

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
                    "session_id": session_id,
                    "message": "ping",
                    "model": smoke_model,
                },
                headers=headers,
            ) as resp:
                if resp.status_code != 200:
                    warn(f"chat HTTP {resp.status_code}", resp.text)
                    errors += 1
                    body = ""
                else:
                    body = resp.read().decode("utf-8")

        events = _parse_sse(body)
        if any(e.get("event") == "done" for e in events):
            out("SSE chat → done", "流式对话链路正常（Agent 已 Mock）")
        else:
            warn("未收到 done 事件", "检查 agent_service SSE")
            errors += 1

        client.delete(f"/api/sessions/{session_id}", headers=headers)

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
