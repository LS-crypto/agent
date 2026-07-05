"""MCPManager 与内置 HTTP MCP 集成测试。"""

from __future__ import annotations

import json
import threading
import time

from core.mcp.builtin_server import start_builtin_mcp_server, stop_builtin_mcp_server
from core.tools.build import build_coding_registry, register_mcp_tools
from server.mcp_manager import MCPManager


def test_mcp_manager_parses_tools_array(monkeypatch) -> None:
    import asyncio

    stop_builtin_mcp_server()
    url = start_builtin_mcp_server("127.0.0.1", 19001)
    monkeypatch.setenv("MCP_HTTP_URL", url)
    try:
        mgr = MCPManager()
        asyncio.run(mgr.start())
        assert mgr.enabled is True
        tools = asyncio.run(mgr.list_tools())
        names = {t["tool"]["name"] for t in tools}
        assert "get_disk_usage" in names
        assert "get_current_time" in names
        assert "calculate" in names
    finally:
        stop_builtin_mcp_server()


def test_register_mcp_tools_imports_into_user_registry(monkeypatch) -> None:
    stop_builtin_mcp_server()
    url = start_builtin_mcp_server("127.0.0.1", 19002)
    monkeypatch.setenv("MCP_HTTP_URL", url)
    try:
        base = build_coding_registry("mcp-test-user", register_mcp=False)
        register_mcp_tools(base)

        user_reg = build_coding_registry("mcp-test-user", register_mcp=True)
        names = {s["function"]["name"] for s in user_reg.get_schemas()}
        assert "get_disk_usage" in names

        result = user_reg.execute("get_current_time", {"timezone_name": "UTC"})
        assert result.get("success") is True
    finally:
        stop_builtin_mcp_server()
