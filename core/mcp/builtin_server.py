"""内置 MCP-like HTTP 服务：暴露系统/Skills 工具，供 MCPManager 或外部客户端调用。"""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 工具名 → handler(user_id, **args)
_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {}


def _register_builtin_handlers(user_id: str = "default") -> None:
    from core.tools.mcp_tools import MCPTools
    from core.tools.skills_tool import SkillsTools
    from core.tools.system import SystemTools

    sys_tools = SystemTools(user_id)
    skill_tools = SkillsTools()
    mcp = MCPTools(user_id)
    _HANDLERS.clear()
    _HANDLERS.update(
        {
            "get_disk_usage": lambda **kw: sys_tools.get_disk_usage(kw.get("path", ".")),
            "get_workspace_stats": lambda **_: sys_tools.get_workspace_stats(),
            "get_env_info": lambda **_: sys_tools.get_env_info(),
            "list_skills": lambda **_: skill_tools.list_skills(),
            "use_skill": lambda **kw: skill_tools.use_skill(kw.get("skill_name", "")),
            "get_current_time": lambda **kw: mcp.get_current_time(
                kw.get("timezone_name", "Asia/Shanghai")
            ),
            "fetch_url": lambda **kw: mcp.fetch_url(
                kw.get("url", ""), kw.get("max_chars", 8000)
            ),
            "memory_note_save": lambda **kw: mcp.memory_note_save(
                kw.get("title", ""), kw.get("content", ""), kw.get("tags", "")
            ),
            "memory_note_search": lambda **kw: mcp.memory_note_search(
                kw.get("query", ""), kw.get("limit", 5)
            ),
            "memory_note_list": lambda **kw: mcp.memory_note_list(kw.get("limit", 20)),
            "calculate": lambda **kw: mcp.calculate(kw.get("expression", "")),
        }
    )


def _tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "get_disk_usage",
            "description": "沙箱磁盘空间 total/used/free",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
        },
        {
            "name": "get_workspace_stats",
            "description": "沙箱项目文件数与总大小",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_env_info",
            "description": "Python/平台/沙箱路径",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "list_skills",
            "description": "可用 Skills 列表",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "use_skill",
            "description": "加载 Skill 正文",
            "parameters": {
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
                "required": ["skill_name"],
            },
        },
        {
            "name": "get_current_time",
            "description": "获取指定时区当前时间",
            "parameters": {
                "type": "object",
                "properties": {"timezone_name": {"type": "string"}},
            },
        },
        {
            "name": "fetch_url",
            "description": "抓取 URL 文本内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "max_chars": {"type": "integer"},
                },
                "required": ["url"],
            },
        },
        {
            "name": "memory_note_save",
            "description": "保存一条记忆笔记",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {"type": "string"},
                },
                "required": ["title", "content"],
            },
        },
        {
            "name": "memory_note_search",
            "description": "搜索记忆笔记",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "memory_note_list",
            "description": "列出记忆笔记",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
        },
        {
            "name": "calculate",
            "description": "安全计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    ]


class _MCPHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("builtin MCP %s", args[0] if args else "")

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/tools", "/tools/"):
            self._json(200, {"tools": _tool_schemas()})
        elif path in ("/health", "/health/"):
            self._json(200, {"status": "ok", "service": "sheldon-builtin-mcp"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/call", "/call/"):
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"success": False, "error": "invalid json"})
            return
        tool = data.get("tool") or data.get("name")
        args = data.get("args") or data.get("arguments") or {}
        if not tool or tool not in _HANDLERS:
            self._json(400, {"success": False, "error": f"unknown tool: {tool}"})
            return
        try:
            result = _HANDLERS[tool](**args)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})


_server: HTTPServer | None = None
_thread: threading.Thread | None = None


def start_builtin_mcp_server(host: str = "127.0.0.1", port: int = 9000) -> str:
    """启动后台 HTTP MCP 服务，返回 base URL。"""
    global _server, _thread
    if _server is not None:
        return f"http://{host}:{port}"

    _register_builtin_handlers()
    _server = HTTPServer((host, port), _MCPHandler)
    _thread = threading.Thread(
        target=_server.serve_forever,
        daemon=True,
        name="builtin-mcp-http",
    )
    _thread.start()
    url = f"http://{host}:{port}"
    logger.info("内置 MCP HTTP 已启动: %s", url)
    return url


def stop_builtin_mcp_server() -> None:
    global _server, _thread
    if _server:
        _server.shutdown()
        _server = None
    _thread = None
