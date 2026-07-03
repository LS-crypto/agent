"""GitHub REST API 公共辅助（Token 头、repo 解析、错误格式化）。"""

from __future__ import annotations

from typing import Any

from core.mcp.config import GITHUB_API_BASE, get_github_config


def github_headers(token: str | None = None) -> dict[str, str]:
    cfg = get_github_config()
    tok = token or cfg.token or ""
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": cfg.api_version,
        "User-Agent": "Sheldon-Agent/1.0",
    }


def resolve_repo(repo: str | None = None) -> str | None:
    cfg = get_github_config()
    raw = (repo or cfg.default_repo or "").strip()
    if not raw or "/" not in raw or raw.count("/") != 1:
        return None
    owner, name = raw.split("/", 1)
    if not owner or not name:
        return None
    return f"{owner}/{name}"


def not_configured_error() -> dict[str, Any]:
    return {
        "success": False,
        "error": "未配置 GITHUB_TOKEN（或 GITHUB_PERSONAL_ACCESS_TOKEN）",
        "hint": "在 .env 设置 Token；可选 GITHUB_DEFAULT_REPO=owner/repo",
        "policy": "github_not_configured",
    }


def repo_required_error() -> dict[str, Any]:
    return {
        "success": False,
        "error": "缺少有效 repo（格式 owner/repo）",
        "hint": "传入 repo 参数或在 .env 设置 GITHUB_DEFAULT_REPO",
    }


def api_error(status: int, data: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(data, dict):
        msg = data.get("message") or data.get("error") or str(data)
    else:
        msg = str(data)
    return {"success": False, "error": f"GitHub API HTTP {status}: {msg}"}


def api_url(path: str) -> str:
    path = path if path.startswith("/") else f"/{path}"
    return f"{GITHUB_API_BASE}{path}"


def github_search_url(path: str, q: str, per_page: int) -> str:
    from urllib.parse import urlencode

    return api_url(f"{path}?{urlencode({'q': q, 'per_page': per_page})}")
