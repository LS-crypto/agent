"""搜索工具：grep / glob，限制在用户沙箱内。"""

from __future__ import annotations

import re
from fnmatch import fnmatch

from core.tools.policy import MAX_GREP_MATCHES, is_sensitive_path
from core.tools.registry import ToolRegistry
from core.tools.sandbox import WorkspaceSandbox


class SearchTools:
    def __init__(self, user_id: str) -> None:
        self.sandbox = WorkspaceSandbox(user_id)

    def _skip_sensitive(self, file_path) -> bool:
        try:
            rel = self.sandbox.rel(file_path)
        except ValueError:
            return True
        return is_sensitive_path(rel)

    def grep(self, pattern: str, path: str = ".") -> dict:
        resolved = self.sandbox.resolve(path, check_sensitive=True)
        if isinstance(resolved, dict):
            return resolved

        matches: list[dict] = []
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return {"success": False, "error": f"无效正则: {e}"}

        files = [resolved] if resolved.is_file() else sorted(resolved.rglob("*"))
        for file_path in files:
            if not file_path.is_file() or self._skip_sensitive(file_path):
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    matches.append(
                        {
                            "file": self.sandbox.rel(file_path),
                            "line": i,
                            "content": line[:200],
                        }
                    )
                    if len(matches) >= MAX_GREP_MATCHES:
                        return {
                            "success": True,
                            "matches": matches,
                            "truncated": True,
                        }

        return {"success": True, "matches": matches, "count": len(matches)}

    def glob_search(self, pattern: str, dir_path: str = ".") -> dict:
        resolved = self.sandbox.resolve(dir_path, check_sensitive=True)
        if isinstance(resolved, dict):
            return resolved
        if not resolved.is_dir():
            return {"success": False, "error": f"目录不存在: {dir_path}"}

        results: list[str] = []
        for item in sorted(resolved.rglob("*")):
            if self._skip_sensitive(item):
                continue
            rel = self.sandbox.rel(item)
            name = item.name
            if fnmatch(name, pattern) or fnmatch(rel, pattern):
                results.append(rel)
            if len(results) >= MAX_GREP_MATCHES:
                break

        return {
            "success": True,
            "pattern": pattern,
            "matches": results,
            "count": len(results),
            "truncated": len(results) >= MAX_GREP_MATCHES,
        }


def register_search_tools(registry: ToolRegistry, user_id: str) -> None:
    search = SearchTools(user_id)
    registry.register(
        name="grep",
        description="在沙箱内用正则搜索文件内容。path 可为文件或目录，默认搜索整个项目。",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "正则表达式"},
                "path": {"type": "string", "description": "相对路径，默认 ."},
            },
            "required": ["pattern"],
        },
        handler=search.grep,
    )
    registry.register(
        name="glob_search",
        description="按文件名模式搜索沙箱内文件，如 *.py 或 **/*.txt。",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "glob 模式，如 *.py"},
                "dir_path": {"type": "string", "description": "起始目录，默认 ."},
            },
            "required": ["pattern"],
        },
        handler=search.glob_search,
    )
