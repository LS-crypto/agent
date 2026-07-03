"""后端请求日志：每行附带中文说明。"""

from __future__ import annotations

import logging
import re

from core.agent.console import out

_log = logging.getLogger("sheldon.agent")

# 按路径匹配中文说明（先匹配更具体的规则）
_ROUTE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^GET /api/models$"), "获取 Agent 可用模型列表"),
    (re.compile(r"^GET /api/mcp/status$"), "获取 MCP 配置与连通状态"),
    (re.compile(r"^GET /api/mcp/catalog$"), "获取 MCP 服务目录"),
    (re.compile(r"^GET /api/sessions$"), "获取会话列表"),
    (re.compile(r"^POST /api/sessions$"), "创建新会话"),
    (re.compile(r"^GET /api/sessions/[^/]+$"), "获取会话详情（含历史消息）"),
    (re.compile(r"^PATCH /api/sessions/[^/]+$"), "重命名会话"),
    (re.compile(r"^POST /api/sessions/[^/]+/reset$"), "清空会话对话"),
    (re.compile(r"^DELETE /api/sessions/[^/]+$"), "删除会话"),
    (re.compile(r"^POST /api/chat$"), "SSE 流式对话（调用 Agent Loop）"),
]


def note_for(method: str, path: str) -> str:
    spec = f"{method.upper()} {path.rstrip('/') or '/'}"
    for pattern, note in _ROUTE_RULES:
        if pattern.match(spec):
            return note
    return "其他 API 请求"


def log_request(
    client: str,
    method: str,
    path: str,
    status: int,
    elapsed_ms: float,
) -> None:
    query = ""
    if "?" in path:
        path, query = path.split("?", 1)
        query = f"?{query}"
    note = note_for(method, path)
    line = f"{client} {method} {path}{query} → {status} ({elapsed_ms:.0f}ms)"
    if _log.handlers:
        _log.info("%s  --%s", line, note)
    else:
        out(line, note)
