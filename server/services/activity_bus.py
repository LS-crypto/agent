"""全局活动广播：服务端终端镜像 + 管理员实时 SSE。"""

from __future__ import annotations

import queue
from collections import deque
from threading import Lock
from typing import Any

from core.agent.console import answer, out, step, tool, tool_result, warn

_lock = Lock()
_subscribers: list[queue.Queue[dict[str, Any]]] = []
_recent: deque[dict[str, Any]] = deque(maxlen=300)


def publish(record: dict[str, Any]) -> None:
    """广播活动记录到订阅者与服务端终端。"""
    with _lock:
        _recent.append(record)
        dead: list[queue.Queue[dict[str, Any]]] = []
        for sub in _subscribers:
            try:
                sub.put_nowait(record)
            except queue.Full:
                dead.append(sub)
        for d in dead:
            if d in _subscribers:
                _subscribers.remove(d)
    _mirror_terminal(record)


def subscribe() -> queue.Queue[dict[str, Any]]:
    q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=200)
    with _lock:
        _subscribers.append(q)
        for item in _recent:
            try:
                q.put_nowait(item)
            except queue.Full:
                break
    return q


def unsubscribe(q: queue.Queue[dict[str, Any]]) -> None:
    with _lock:
        if q in _subscribers:
            _subscribers.remove(q)


def _mirror_terminal(record: dict[str, Any]) -> None:
    """服务端终端实时输出用户活动（不含 API Key 等敏感字段）。"""
    event = record.get("event", "")
    user_id = record.get("user_id", "?")
    t = record.get("time", "")

    if event == "session_start":
        step("用户活动", f"[{user_id}] 开始会话（{t}）")
    elif event == "user_message":
        content = str(record.get("content", ""))[:500]
        out(f"[{user_id}] 提问：{content}", f"{t} 用户消息")
    elif event == "tool_call":
        tool(
            record.get("tool", "?"),
            record.get("args") or {},
            f"[{user_id}] {t} 调用工具",
        )
    elif event == "tool_result":
        preview = str(record.get("preview", ""))[:200]
        tool_result(preview, f"[{user_id}] {t} 工具完成")
    elif event == "assistant_reply":
        preview = str(record.get("content", ""))[:200]
        answer(preview, f"[{user_id}] {t} 回复")
    elif event == "error":
        warn(str(record.get("message", "")), f"[{user_id}] {t} 错误")
    elif event == "session_end":
        step("用户活动", f"[{user_id}] 结束会话（{t}）")
