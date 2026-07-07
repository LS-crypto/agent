"""工具注册表：统一管理 Schema 与执行函数。"""

from __future__ import annotations

import json
from typing import Any, Callable


class ToolRegistry:
    """工具注册表 — 注册、获取 Schema、执行工具。"""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., dict[str, Any]]] = {}
        self._schemas: list[dict[str, Any]] = []

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., dict[str, Any]],
    ) -> None:
        self._handlers[name] = handler
        self._schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            }
        )

    def get_schemas(self) -> list[dict[str, Any]]:
        return self._schemas

    def import_tools(self, source: ToolRegistry, names: list[str]) -> None:
        """从另一注册表复制指定工具（用于共享 MCP 工具）。"""
        wanted = set(names)
        for schema in source._schemas:
            name = schema["function"]["name"]
            if name in wanted and name not in self._handlers:
                self._handlers[name] = source._handlers[name]
                self._schemas.append(schema)

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        handler = self._handlers.get(name)
        if not handler:
            return {"success": False, "error": f"未知工具: {name}"}
        try:
            return handler(**args)
        except TypeError as e:
            return {"success": False, "error": f"参数错误: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def result_text(result: dict[str, Any]) -> str:
        """工具结果序列化为模型可读的字符串。"""
        return json.dumps(result, ensure_ascii=False)
