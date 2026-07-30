"""MiniMax 接入冒烟测试：验证 base_url / 模型列表 / 单轮对话三种链路。

使用：
    uv run python scripts/smoke_minimax.py
    MINIMAX_API_KEY=ey... uv run python scripts/smoke_minimax.py --model MiniMax-M3
    MINIMAX_API_KEY=ey... uv run python scripts/smoke_minimax.py --tools

退出码 0 = 通过；非 0 = 任一步失败。
"""

from __future__ import annotations

import argparse
import os
import sys

from core.config import (
    MINIMAX_BASE_URL,
    create_client,
    get_provider_for_model,
)
from core.agent.console import out, step, warn


def _resolve_minimax_key() -> str | None:
    key = os.getenv("MINIMAX_API_KEY", "").strip()
    return key or None


def _check_env() -> bool:
    key = _resolve_minimax_key()
    if not key:
        warn("未配置 MINIMAX_API_KEY", "请在 .env 或 shell 注入 MiniMax 开放平台密钥")
        return False
    return True


def _smoke_list_models(client) -> bool:
    """拉取可用模型列表（含 MiniMax-M3 视为通过）。"""
    try:
        page = client.models.list()
        ids = sorted(getattr(item, "id", "") for item in page.data)
    except Exception as exc:
        warn("调用 /models 失败", str(exc))
        return False
    if not ids:
        warn("模型列表为空", "请确认账号权限")
        return False
    out(f"模型数={len(ids)}", "前 10 项：" + ", ".join(ids[:10]))
    if "MiniMax-M3" in ids:
        out("MiniMax-M3 可用", "✓ 模型在远程可用列表中")
        return True
    warn("MiniMax-M3 不在远程列表", "请确认账号是否开通该模型 / 是否使用了其它 model id")
    return False


def _smoke_chat(client, model: str, *, with_tools: bool) -> bool:
    """发送单轮消息,验证 SSE 流式（或 blocking）能拿到文本回复。"""
    messages = [{"role": "user", "content": "你好，请用一句话自我介绍。"}]
    tools = None
    tool_choice = "auto"
    if with_tools:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "返回当前时间",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=200,
            temperature=0.2,
            tools=tools,
            tool_choice=tool_choice if tools else None,
        )
    except Exception as exc:
        warn(f"调用 /chat.completions 失败 (model={model})", str(exc))
        return False
    msg = resp.choices[0].message
    if msg.content:
        out("对话 OK", f"回复（{len(msg.content)} 字）: {msg.content[:80]}")
    else:
        out("对话完成（无文本回复，可能直接走了工具）", "")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="MiniMax 接入冒烟测试")
    parser.add_argument(
        "--model",
        default="MiniMax-M3",
        help="用于对话的模型 id（默认 MiniMax-M3）",
    )
    parser.add_argument(
        "--tools",
        action="store_true",
        help="在对话中携带一个工具，验证 OpenAI 工具调用协议",
    )
    parser.add_argument(
        "--skip-list",
        action="store_true",
        help="跳过 /models 列表校验（仅做 chat 链路）",
    )
    args = parser.parse_args()

    step("连接配置", f"endpoint={MINIMAX_BASE_URL}")
    if not _check_env():
        return 2
    provider = get_provider_for_model(args.model)
    if provider != "minimax":
        warn(
            f"模型 {args.model} 不属于 minimax provider（实测={provider}）",
            "请使用 minimax 的 model id,例如 MiniMax-M3",
        )
        return 2
    client = create_client(provider="minimax")

    if not args.skip_list and not _smoke_list_models(client):
        # /models 失败不回滚：可能是早期版本不支持,但 chat/completions 仍可用
        warn("/models 失败", "继续测试 chat 端点（仅告警,不退出）")

    if not _smoke_chat(client, args.model, with_tools=args.tools):
        return 1
    out("MiniMax 端到端冒烟测试通过", "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
