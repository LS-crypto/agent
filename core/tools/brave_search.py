"""Brave Search MCP 兼容工具：联网 Web / 新闻搜索。"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from core.mcp.client import http_get
from core.mcp.config import BRAVE_API_BASE, get_brave_config
from core.tools.registry import ToolRegistry

_MAX_RESULTS = 20
_DESC_PREVIEW = 280


def _not_configured() -> dict[str, Any]:
    return {
        "success": False,
        "error": "未配置 BRAVE_API_KEY",
        "hint": "在 .env 设置 BRAVE_API_KEY；搜索前需用户确认（review 档位）",
        "policy": "brave_not_configured",
    }


def _brave_headers() -> dict[str, str]:
    cfg = get_brave_config()
    return {
        "Accept": "application/json",
        "X-Subscription-Token": cfg.api_key or "",
        "User-Agent": "Sheldon-Agent/1.0",
    }


def _parse_web_results(data: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    web = data.get("web") or {}
    results = web.get("results") or []
    out: list[dict[str, Any]] = []
    for item in results[:limit]:
        out.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "description": (item.get("description") or "")[:_DESC_PREVIEW],
                "age": item.get("age"),
            }
        )
    return out


def _parse_news_results(data: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    results = data.get("results") or []
    out: list[dict[str, Any]] = []
    for item in results[:limit]:
        out.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "description": (item.get("description") or "")[:_DESC_PREVIEW],
                "source": item.get("source"),
                "age": item.get("age"),
            }
        )
    return out


class BraveSearchTools:
    """Brave Search API 工具集。"""

    def brave_web_search(self, query: str, count: int | None = None) -> dict[str, Any]:
        cfg = get_brave_config()
        if not cfg.configured:
            return _not_configured()

        q = query.strip()
        if not q:
            return {"success": False, "error": "query 不能为空"}

        n = count if count is not None else cfg.default_count
        n = max(1, min(int(n), _MAX_RESULTS))

        url = f"{BRAVE_API_BASE}/web/search?q={quote(q)}&count={n}"
        status, data = http_get(url, headers=_brave_headers(), timeout=20)
        if status != 200 or not isinstance(data, dict):
            msg = data if isinstance(data, str) else (
                data.get("message") if isinstance(data, dict) else str(data)
            )
            return {"success": False, "error": f"Brave API HTTP {status}: {msg}"}

        results = _parse_web_results(data, n)
        return {
            "success": True,
            "query": q,
            "results": results,
            "count": len(results),
            "note": "单页详情请用 fetch_url；搜索走 Brave",
        }

    def brave_news_search(self, query: str, count: int | None = None) -> dict[str, Any]:
        cfg = get_brave_config()
        if not cfg.configured:
            return _not_configured()

        q = query.strip()
        if not q:
            return {"success": False, "error": "query 不能为空"}

        n = count if count is not None else min(cfg.default_count, 10)
        n = max(1, min(int(n), _MAX_RESULTS))

        url = f"{BRAVE_API_BASE}/news/search?q={quote(q)}&count={n}"
        status, data = http_get(url, headers=_brave_headers(), timeout=20)
        if status != 200 or not isinstance(data, dict):
            msg = data if isinstance(data, str) else (
                data.get("message") if isinstance(data, dict) else str(data)
            )
            return {"success": False, "error": f"Brave API HTTP {status}: {msg}"}

        results = _parse_news_results(data, n)
        return {
            "success": True,
            "query": q,
            "results": results,
            "count": len(results),
        }


def register_brave_search_tools(registry: ToolRegistry) -> None:
    tools = BraveSearchTools()

    registry.register(
        "brave_web_search",
        "Brave 联网 Web 搜索（需 BRAVE_API_KEY）。返回标题、URL、摘要；单页内容用 fetch_url。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "count": {"type": "integer", "description": "结果条数，默认 BRAVE_SEARCH_COUNT"},
            },
            "required": ["query"],
        },
        tools.brave_web_search,
    )
    registry.register(
        "brave_news_search",
        "Brave 新闻搜索（需 BRAVE_API_KEY）。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["query"],
        },
        tools.brave_news_search,
    )
