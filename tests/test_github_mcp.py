"""GitHub MCP 工具测试（Mock HTTP，不消耗 API 配额）。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.tools.github_mcp import GitHubMCPTools
from core.tools.registry import ToolRegistry
from core.tools.build import build_coding_registry


@pytest.fixture
def gh_tools(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    monkeypatch.setenv("GITHUB_DEFAULT_REPO", "octocat/Hello-World")
    return GitHubMCPTools()


def test_not_configured(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_PERSONAL_ACCESS_TOKEN", raising=False)
    tools = GitHubMCPTools()
    r = tools.github_search_issues("bug")
    assert r["success"] is False
    assert "GITHUB_TOKEN" in r["error"]


def test_repo_required(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.delenv("GITHUB_DEFAULT_REPO", raising=False)
    tools = GitHubMCPTools()
    r = tools.github_list_pulls()
    assert r["success"] is False
    assert "repo" in r["error"].lower()


def test_search_issues_mock(gh_tools):
    payload = {
        "total_count": 1,
        "items": [
            {
                "number": 42,
                "title": "Fix bug",
                "state": "open",
                "user": {"login": "octocat"},
                "labels": [{"name": "bug"}],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
                "html_url": "https://github.com/octocat/Hello-World/issues/42",
                "body": "Something broken",
            }
        ],
    }
    with patch("core.tools.github_mcp.http_get", return_value=(200, payload)):
        r = gh_tools.github_search_issues("bug")
    assert r["success"] is True
    assert r["count"] == 1
    assert r["issues"][0]["number"] == 42


def test_get_issue_with_comments_mock(gh_tools):
    issue = {
        "number": 1,
        "title": "First",
        "state": "open",
        "user": {"login": "octocat"},
        "labels": [],
        "body": "Body text",
        "html_url": "https://github.com/octocat/Hello-World/issues/1",
    }
    comments = [
        {"user": {"login": "dev"}, "created_at": "2024-01-03T00:00:00Z", "body": "LGTM"},
    ]

    def fake_get(url, **kwargs):
        if url.endswith("/comments?per_page=5"):
            return 200, comments
        return 200, issue

    with patch("core.tools.github_mcp.http_get", side_effect=fake_get):
        r = gh_tools.github_get_issue(1)
    assert r["success"] is True
    assert r["issue"]["title"] == "First"
    assert len(r["comments"]) == 1


def test_list_pulls_mock(gh_tools):
    pulls = [
        {
            "number": 7,
            "title": "Feature",
            "state": "open",
            "user": {"login": "dev"},
            "draft": False,
            "merged": False,
            "html_url": "https://github.com/octocat/Hello-World/pull/7",
            "body": "PR body",
        }
    ]
    with patch("core.tools.github_mcp.http_get", return_value=(200, pulls)):
        r = gh_tools.github_list_pulls(state="open")
    assert r["success"] is True
    assert r["pulls"][0]["number"] == 7


def test_search_code_mock(gh_tools):
    payload = {
        "total_count": 1,
        "items": [
            {
                "name": "main.py",
                "path": "src/main.py",
                "sha": "abc123def456",
                "html_url": "https://github.com/octocat/Hello-World/blob/main/src/main.py",
                "repository": {"full_name": "octocat/Hello-World"},
            }
        ],
    }
    with patch("core.tools.github_mcp.http_get", return_value=(200, payload)):
        r = gh_tools.github_search_code("def main")
    assert r["success"] is True
    assert r["results"][0]["path"] == "src/main.py"


def test_registry_includes_github_tools(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    reg = build_coding_registry("default", register_mcp=False)
    names = {s["function"]["name"] for s in reg.get_schemas()}
    assert "github_search_issues" in names
    assert "github_get_pull" in names


def test_registry_execute_unknown_github(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_PERSONAL_ACCESS_TOKEN", raising=False)
    reg = ToolRegistry()
    from core.tools.github_mcp import register_github_mcp_tools

    register_github_mcp_tools(reg)
    r = reg.execute("github_search_issues", {"query": "x"})
    assert r["success"] is False
