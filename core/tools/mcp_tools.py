"""热门 MCP 兼容工具（本地安全实现，参考 GitHub MCP 生态）。"""

from __future__ import annotations

import ast
import json
import operator as op
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core.tools.registry import ToolRegistry
from core.user.paths import workspace_projects

# 参考 MCP Fetch / Brave 等：只读抓取，域名白名单
_FETCH_ALLOW_HOSTS = frozenset(
    {
        "github.com",
        "raw.githubusercontent.com",
        "gist.githubusercontent.com",
        "docs.python.org",
        "pypi.org",
        "npmjs.com",
        "developer.mozilla.org",
        "stackoverflow.com",
        "modelcontextprotocol.io",
    }
)
_MAX_FETCH_BYTES = 48_000

_SAFE_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}


def _notes_path(user_id: str) -> Path:
    p = workspace_projects(user_id).parent / "memory_notes.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_notes(user_id: str) -> list[dict[str, Any]]:
    path = _notes_path(user_id)
    if not path.is_file():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_notes(user_id: str, notes: list[dict[str, Any]]) -> None:
    _notes_path(user_id).write_text(
        json.dumps(notes[-200:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class MCPTools:
    """MCP 风格工具集：Time · Fetch · Memory · Calculate。"""

    def __init__(self, user_id: str = "default") -> None:
        self.user_id = user_id

    def get_current_time(self, timezone_name: str = "Asia/Shanghai") -> dict:
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = timezone.utc
            timezone_name = "UTC"
        now = datetime.now(tz)
        return {
            "success": True,
            "iso": now.isoformat(),
            "timezone": timezone_name,
            "weekday": now.strftime("%A"),
            "unix": int(now.timestamp()),
        }

    def fetch_url(self, url: str, max_chars: int = 8000) -> dict:
        """参考 MCP Fetch：HTTPS GET，域名白名单，纯文本摘要。"""
        url = url.strip()
        if not url.startswith("https://"):
            return {"success": False, "error": "仅允许 https:// URL", "policy": "fetch_blocked"}

        try:
            from urllib.parse import urlparse

            host = urlparse(url).netloc.lower().split(":")[0]
            if host not in _FETCH_ALLOW_HOSTS and not host.endswith(".github.io"):
                allowed = ", ".join(sorted(_FETCH_ALLOW_HOSTS)[:6]) + " 等"
                return {
                    "success": False,
                    "error": f"域名不在白名单: {host}。允许: {allowed}",
                    "policy": "fetch_blocked",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

        max_chars = min(max(max_chars, 500), 20_000)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Sheldon-Agent/1.0 (MCP-fetch-compat)"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read(_MAX_FETCH_BYTES)
                ctype = resp.headers.get("Content-Type", "")
            text = raw.decode("utf-8", errors="replace")
            # 粗略去 HTML 标签
            if "html" in ctype.lower():
                text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
                text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
            preview = text[:max_chars]
            return {
                "success": True,
                "url": url,
                "content_type": ctype,
                "length": len(text),
                "preview": preview,
                "truncated": len(text) > max_chars,
            }
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def memory_note_save(self, title: str, content: str, tags: str = "") -> dict:
        notes = _load_notes(self.user_id)
        entry = {
            "id": len(notes) + 1,
            "title": title[:200],
            "content": content[:4000],
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        notes.append(entry)
        _save_notes(self.user_id, notes)
        return {"success": True, "note_id": entry["id"], "title": entry["title"]}

    def memory_note_search(self, query: str, limit: int = 5) -> dict:
        q = query.lower()
        hits = []
        for n in reversed(_load_notes(self.user_id)):
            blob = f"{n.get('title', '')} {n.get('content', '')} {' '.join(n.get('tags', []))}".lower()
            if q in blob:
                hits.append(n)
            if len(hits) >= limit:
                break
        return {"success": True, "query": query, "notes": hits, "count": len(hits)}

    def memory_note_list(self, limit: int = 20) -> dict:
        notes = _load_notes(self.user_id)[-limit:]
        return {
            "success": True,
            "notes": [
                {"id": n["id"], "title": n["title"], "tags": n.get("tags", [])}
                for n in reversed(notes)
            ],
            "count": len(notes),
        }

    def calculate(self, expression: str) -> dict:
        """安全数学表达式（参考 MCP calculate / 无 eval）。"""
        expr = expression.strip()
        if not expr or len(expr) > 200:
            return {"success": False, "error": "表达式无效或过长"}
        if not re.match(r"^[\d\s+\-*/%.()]+$", expr):
            return {"success": False, "error": "仅允许数字与 +-*/%.() 运算符"}

        try:
            node = ast.parse(expr, mode="eval").body
            result = _eval_ast(node)
            return {"success": True, "expression": expr, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


def _eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_ast(node.operand))
    raise ValueError("不支持的表达式")


def register_mcp_compat_tools(registry: ToolRegistry, user_id: str = "default") -> None:
    tools = MCPTools(user_id)

    registry.register(
        "get_current_time",
        "获取当前日期时间（参考 MCP Time）。可指定 IANA 时区如 Asia/Shanghai。",
        {
            "type": "object",
            "properties": {
                "timezone_name": {
                    "type": "string",
                    "description": "IANA 时区，默认 Asia/Shanghai",
                },
            },
        },
        tools.get_current_time,
    )
    registry.register(
        "fetch_url",
        "HTTPS 抓取网页/文档正文（参考 MCP Fetch）。仅白名单域名：GitHub、PyPI、MDN 等。",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "https:// 开头 URL"},
                "max_chars": {"type": "integer", "description": "返回最大字符，默认 8000"},
            },
            "required": ["url"],
        },
        tools.fetch_url,
    )
    registry.register(
        "memory_note_save",
        "保存一条会话记忆笔记（参考 MCP Memory）。存于用户 runtime 目录。",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "string", "description": "逗号分隔标签"},
            },
            "required": ["title", "content"],
        },
        tools.memory_note_save,
    )
    registry.register(
        "memory_note_search",
        "按关键词搜索已保存的记忆笔记。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        tools.memory_note_search,
    )
    registry.register(
        "memory_note_list",
        "列出最近保存的记忆笔记标题。",
        {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
        },
        tools.memory_note_list,
    )
    registry.register(
        "calculate",
        "安全计算数学表达式（+-*/% 与括号）。",
        {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
        tools.calculate,
    )
