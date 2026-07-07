"""MCP 兼容工具测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.tools.mcp_tools import MCPTools


@pytest.fixture
def mcp_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MCPTools:
    root = tmp_path / "workspaces" / "u" / "projects"
    root.mkdir(parents=True)
    monkeypatch.setattr(
        "core.tools.mcp_tools.workspace_projects",
        lambda _uid: root,
    )
    return MCPTools("u")


def test_get_current_time(mcp_tools: MCPTools) -> None:
    r = mcp_tools.get_current_time("Asia/Shanghai")
    assert r["success"] is True
    assert "iso" in r


def test_calculate(mcp_tools: MCPTools) -> None:
    assert mcp_tools.calculate("(1+2)*3")["result"] == 9.0
    assert mcp_tools.calculate("__import__('os')")["success"] is False


def test_fetch_url_blocked_domain(mcp_tools: MCPTools) -> None:
    r = mcp_tools.fetch_url("https://evil.example.com/x")
    assert r["success"] is False
    assert "白名单" in r["error"]


def test_memory_notes(mcp_tools: MCPTools) -> None:
    save = mcp_tools.memory_note_save("t", "hello world", tags="demo")
    assert save["success"] is True
    found = mcp_tools.memory_note_search("hello")
    assert found["count"] >= 1
