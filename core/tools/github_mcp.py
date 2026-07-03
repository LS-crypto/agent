"""GitHub MCP 兼容工具：Issues / PR / 代码搜索（REST 直连）。"""

from __future__ import annotations

from typing import Any

from core.mcp.client import http_get
from core.mcp.config import get_github_config
from core.mcp.github_api import (
    api_error,
    api_url,
    github_headers,
    github_search_url,
    not_configured_error,
    repo_required_error,
    resolve_repo,
)
from core.tools.registry import ToolRegistry

_MAX_ISSUES = 15
_MAX_COMMENTS = 5
_MAX_PULLS = 15
_MAX_CODE = 10
_BODY_PREVIEW = 400


def _configured() -> bool:
    return get_github_config().configured


def _summarize_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": item.get("number"),
        "title": item.get("title"),
        "state": item.get("state"),
        "user": (item.get("user") or {}).get("login"),
        "labels": [l.get("name") for l in item.get("labels") or []],
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "html_url": item.get("html_url"),
        "body_preview": (item.get("body") or "")[:_BODY_PREVIEW],
    }


def _summarize_pull(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": item.get("number"),
        "title": item.get("title"),
        "state": item.get("state"),
        "user": (item.get("user") or {}).get("login"),
        "draft": item.get("draft"),
        "merged": item.get("merged"),
        "created_at": item.get("created_at"),
        "html_url": item.get("html_url"),
        "body_preview": (item.get("body") or "")[:_BODY_PREVIEW],
    }


class GitHubMCPTools:
    """GitHub 只读 API 工具集。"""

    def github_search_issues(
        self,
        query: str,
        repo: str | None = None,
        state: str = "open",
        limit: int = 10,
    ) -> dict[str, Any]:
        if not _configured():
            return not_configured_error()
        resolved = resolve_repo(repo)
        if not resolved:
            return repo_required_error()

        q = query.strip()
        if not q:
            return {"success": False, "error": "query 不能为空"}

        limit = max(1, min(int(limit), _MAX_ISSUES))
        state_q = state.strip().lower() if state else "open"
        if state_q not in ("open", "closed", "all"):
            state_q = "open"

        if state_q == "all":
            search_q = f"repo:{resolved} is:issue {q}".strip()
        else:
            search_q = f"repo:{resolved} is:issue state:{state_q} {q}".strip()

        url = github_search_url("/search/issues", search_q, limit)
        status, data = http_get(url, headers=github_headers(), timeout=20)
        if status != 200 or not isinstance(data, dict):
            return api_error(status, data)

        items = [_summarize_issue(i) for i in (data.get("items") or [])[:limit]]
        return {
            "success": True,
            "repo": resolved,
            "query": q,
            "state": state_q,
            "total_count": data.get("total_count", len(items)),
            "issues": items,
            "count": len(items),
        }

    def github_get_issue(
        self,
        issue_number: int,
        repo: str | None = None,
        include_comments: bool = True,
    ) -> dict[str, Any]:
        if not _configured():
            return not_configured_error()
        resolved = resolve_repo(repo)
        if not resolved:
            return repo_required_error()

        owner, name = resolved.split("/", 1)
        url = api_url(f"/repos/{owner}/{name}/issues/{int(issue_number)}")
        status, data = http_get(url, headers=github_headers(), timeout=20)
        if status != 200 or not isinstance(data, dict):
            return api_error(status, data)

        issue = _summarize_issue(data)
        issue["body"] = (data.get("body") or "")[:2000]

        comments: list[dict[str, Any]] = []
        if include_comments:
            curl = api_url(f"/repos/{owner}/{name}/issues/{int(issue_number)}/comments?per_page={_MAX_COMMENTS}")
            cstatus, cdata = http_get(curl, headers=github_headers(), timeout=15)
            if cstatus == 200 and isinstance(cdata, list):
                for c in cdata[:_MAX_COMMENTS]:
                    comments.append(
                        {
                            "user": (c.get("user") or {}).get("login"),
                            "created_at": c.get("created_at"),
                            "body_preview": (c.get("body") or "")[:300],
                        }
                    )

        return {
            "success": True,
            "repo": resolved,
            "issue": issue,
            "comments": comments,
            "comment_count": len(comments),
        }

    def github_list_pulls(
        self,
        repo: str | None = None,
        state: str = "open",
        limit: int = 10,
    ) -> dict[str, Any]:
        if not _configured():
            return not_configured_error()
        resolved = resolve_repo(repo)
        if not resolved:
            return repo_required_error()

        limit = max(1, min(int(limit), _MAX_PULLS))
        state_q = state.strip().lower() if state else "open"
        if state_q not in ("open", "closed", "all"):
            state_q = "open"

        owner, name = resolved.split("/", 1)
        url = api_url(f"/repos/{owner}/{name}/pulls?state={state_q}&per_page={limit}")
        status, data = http_get(url, headers=github_headers(), timeout=20)
        if status != 200 or not isinstance(data, list):
            return api_error(status, data if isinstance(data, (dict, str)) else str(data))

        pulls = [_summarize_pull(p) for p in data[:limit]]
        return {
            "success": True,
            "repo": resolved,
            "state": state_q,
            "pulls": pulls,
            "count": len(pulls),
        }

    def github_get_pull(
        self,
        pull_number: int,
        repo: str | None = None,
    ) -> dict[str, Any]:
        if not _configured():
            return not_configured_error()
        resolved = resolve_repo(repo)
        if not resolved:
            return repo_required_error()

        owner, name = resolved.split("/", 1)
        url = api_url(f"/repos/{owner}/{name}/pulls/{int(pull_number)}")
        status, data = http_get(url, headers=github_headers(), timeout=20)
        if status != 200 or not isinstance(data, dict):
            return api_error(status, data)

        pull = _summarize_pull(data)
        pull["body"] = (data.get("body") or "")[:2000]
        pull["mergeable"] = data.get("mergeable")
        pull["head"] = (data.get("head") or {}).get("ref")
        pull["base"] = (data.get("base") or {}).get("ref")
        return {"success": True, "repo": resolved, "pull": pull}

    def github_search_code(
        self,
        query: str,
        repo: str | None = None,
        limit: int = 8,
    ) -> dict[str, Any]:
        if not _configured():
            return not_configured_error()
        resolved = resolve_repo(repo)
        if not resolved:
            return repo_required_error()

        q = query.strip()
        if not q:
            return {"success": False, "error": "query 不能为空"}

        limit = max(1, min(int(limit), _MAX_CODE))
        search_q = f"repo:{resolved} {q}".strip()
        url = github_search_url("/search/code", search_q, limit)
        status, data = http_get(url, headers=github_headers(), timeout=25)
        if status != 200 or not isinstance(data, dict):
            return api_error(status, data)

        hits = []
        for item in (data.get("items") or [])[:limit]:
            hits.append(
                {
                    "name": item.get("name"),
                    "path": item.get("path"),
                    "sha": (item.get("sha") or "")[:12],
                    "html_url": item.get("html_url"),
                    "repository": (item.get("repository") or {}).get("full_name"),
                }
            )
        return {
            "success": True,
            "repo": resolved,
            "query": q,
            "total_count": data.get("total_count", len(hits)),
            "results": hits,
            "count": len(hits),
            "note": "代码搜索 API 限流较严，请控制调用频率",
        }


def register_github_mcp_tools(registry: ToolRegistry) -> None:
    tools = GitHubMCPTools()

    registry.register(
        "github_search_issues",
        "在指定 GitHub 仓库搜索 Issue（需 GITHUB_TOKEN）。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "repo": {"type": "string", "description": "owner/repo，默认 GITHUB_DEFAULT_REPO"},
                "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Issue 状态"},
                "limit": {"type": "integer", "description": "返回条数，默认 10"},
            },
            "required": ["query"],
        },
        tools.github_search_issues,
    )
    registry.register(
        "github_get_issue",
        "获取 GitHub Issue 详情与最近评论摘要。",
        {
            "type": "object",
            "properties": {
                "issue_number": {"type": "integer"},
                "repo": {"type": "string"},
                "include_comments": {"type": "boolean", "description": "是否拉取评论，默认 true"},
            },
            "required": ["issue_number"],
        },
        tools.github_get_issue,
    )
    registry.register(
        "github_list_pulls",
        "列出 GitHub 仓库 Pull Request。",
        {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "state": {"type": "string", "enum": ["open", "closed", "all"]},
                "limit": {"type": "integer"},
            },
        },
        tools.github_list_pulls,
    )
    registry.register(
        "github_get_pull",
        "获取 GitHub PR 详情。",
        {
            "type": "object",
            "properties": {
                "pull_number": {"type": "integer"},
                "repo": {"type": "string"},
            },
            "required": ["pull_number"],
        },
        tools.github_get_pull,
    )
    registry.register(
        "github_search_code",
        "在 GitHub 仓库内搜索代码（限流较严，慎用）。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "repo": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        tools.github_search_code,
    )
