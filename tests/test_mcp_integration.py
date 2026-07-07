"""MCP 集成冒烟：工具注册 + 状态 API（不依赖外部 MCP 进程）。"""

from __future__ import annotations

from core.tools.build import build_coding_registry
from fastapi.testclient import TestClient

from server.main import app


def test_mcp_tools_registered_in_registry() -> None:
    registry = build_coding_registry("ci-user", register_mcp=False)
    names = {schema["function"]["name"] for schema in registry.get_schemas()}

    assert "github_search_issues" in names
    assert "github_list_pulls" in names
    assert "brave_web_search" in names
    assert "get_current_time" in names


def test_mcp_registration_and_call() -> None:
    """兼容旧 CI 用例名：验证内置 MCP 兼容工具可调用。"""
    registry = build_coding_registry("ci-user", register_mcp=False)
    result = registry.execute("get_current_time", {"timezone_name": "UTC"})
    assert isinstance(result, dict)
    assert result.get("success") is True
    assert "iso" in result


def test_mcp_status_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/mcp/status?ping=false")

    assert response.status_code == 200
    body = response.json()
    service_ids = {service["id"] for service in body["services"]}
    assert "github" in service_ids
    assert "brave" in service_ids
