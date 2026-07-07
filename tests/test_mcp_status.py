"""MCP 状态 API 与探测测试。"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from core.mcp.status import list_mcp_status, probe_github
from core.tools.policy import get_tool_risk
from server.main import app


def test_github_tools_policy():
    assert get_tool_risk("github_search_issues") == "allowed"
    assert get_tool_risk("github_create_issue_comment") == "review"
    assert get_tool_risk("brave_web_search") == "review"


def test_list_mcp_status_no_tokens(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_PERSONAL_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    data = list_mcp_status(ping=False)
    assert "services" in data
    gh = next(s for s in data["services"] if s["id"] == "github")
    br = next(s for s in data["services"] if s["id"] == "brave")
    assert gh["configured"] is False
    assert br["configured"] is False


def test_probe_github_configured_no_ping(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_12345")
    r = probe_github(ping=False)
    assert r["configured"] is True
    assert r["connected"] is False


def test_api_mcp_status():
    with TestClient(app) as client:
        res = client.get("/api/mcp/status?ping=false")
    assert res.status_code == 200
    body = res.json()
    assert len(body["services"]) >= 3
    ids = {s["id"] for s in body["services"]}
    assert "github" in ids
    assert "brave" in ids


def test_probe_github_connected_mock(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    with patch("core.mcp.status.http_get", return_value=(200, {"login": "octocat"})):
        r = probe_github(ping=True)
    assert r["connected"] is True
    assert r["login"] == "octocat"
