"""MCP 连通性探测：配置状态 + 可选轻量 ping。"""

from __future__ import annotations

from typing import Any

from core.mcp.client import http_get
from core.mcp.config import (
    BRAVE_API_BASE,
    GITHUB_API_BASE,
    get_brave_config,
    get_builtin_mcp_url,
    get_github_config,
)


def _github_headers(token: str) -> dict[str, str]:
    cfg = get_github_config()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": cfg.api_version,
        "User-Agent": "Sheldon-Agent/1.0",
    }


def probe_github(*, ping: bool = True) -> dict[str, Any]:
    cfg = get_github_config()
    base: dict[str, Any] = {
        "id": "github",
        "name": "GitHub MCP",
        "configured": cfg.configured,
        "default_repo": cfg.default_repo,
        "connected": False,
        "message": "",
    }
    if not cfg.configured:
        base["message"] = "未配置 GITHUB_TOKEN（或 GITHUB_PERSONAL_ACCESS_TOKEN）"
        return base
    if not ping:
        base["message"] = "已配置 Token（未探测连通性）"
        return base

    status, data = http_get(f"{GITHUB_API_BASE}/user", headers=_github_headers(cfg.token), timeout=10)
    if status == 200 and isinstance(data, dict):
        base["connected"] = True
        base["message"] = f"已连接 GitHub 用户: {data.get('login', '?')}"
        base["login"] = data.get("login")
        return base
    err = data if isinstance(data, str) else (data.get("message") if isinstance(data, dict) else str(data))
    base["message"] = f"GitHub API 失败 HTTP {status}: {err}"
    return base


def probe_brave(*, ping: bool = True) -> dict[str, Any]:
    cfg = get_brave_config()
    base: dict[str, Any] = {
        "id": "brave",
        "name": "Brave Search MCP",
        "configured": cfg.configured,
        "connected": False,
        "message": "",
    }
    if not cfg.configured:
        base["message"] = "未配置 BRAVE_API_KEY"
        return base
    if not ping:
        base["message"] = "已配置 API Key（未探测连通性）"
        return base

    url = f"{BRAVE_API_BASE}/web/search?q=ping&count=1"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": cfg.api_key,
        "User-Agent": "Sheldon-Agent/1.0",
    }
    status, data = http_get(url, headers=headers, timeout=12)
    if status == 200 and isinstance(data, dict):
        base["connected"] = True
        base["message"] = "Brave Search API 连通正常"
        return base
    err = data if isinstance(data, str) else (data.get("message") if isinstance(data, dict) else str(data))
    base["message"] = f"Brave API 失败 HTTP {status}: {err}"
    return base


def probe_builtin(*, ping: bool = True) -> dict[str, Any]:
    url = get_builtin_mcp_url()
    base: dict[str, Any] = {
        "id": "sheldon-builtin",
        "name": "Sheldon 内置 MCP",
        "configured": True,
        "url": url,
        "connected": False,
        "message": "",
    }
    if not ping:
        base["message"] = f"内置服务地址 {url}"
        return base

    status, data = http_get(f"{url}/health", timeout=3)
    if status == 200:
        base["connected"] = True
        base["message"] = "内置 MCP HTTP 运行中"
        return base
    base["message"] = f"内置 MCP 未响应（{url}/health HTTP {status}），server 是否已启动？"
    return base


def list_mcp_status(*, ping: bool = False) -> dict[str, Any]:
    """汇总各 MCP 配置与连通状态。"""
    services = [
        probe_builtin(ping=ping),
        probe_github(ping=ping),
        probe_brave(ping=ping),
    ]
    return {
        "services": services,
        "any_configured_external": any(
            s["configured"] and s["id"] in ("github", "brave") for s in services
        ),
        "ping_performed": ping,
        "hint": "配置 GITHUB_TOKEN / BRAVE_API_KEY 后可用对应工具；?ping=true 探测连通性",
    }
