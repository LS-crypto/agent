"""工具结果智能压缩：在工具输出送入 LLM 上下文前裁剪，减少 token 消耗。"""

from __future__ import annotations

import json
import re
from typing import Any

# ---------- 压缩配置 ----------

# 各工具输出的最大字符数
MAX_RESULT_CHARS: dict[str, int] = {
    "read_file": 8000,
    "list_dir": 4000,
    "grep": 4000,
    "glob_search": 2000,
    "execute_command": 6000,
    "write_file": 500,
    "edit_file": 500,
}

DEFAULT_MAX_CHARS = 6000

# head/tail 保留行数
HEAD_LINES = 30
TAIL_LINES = 30


# ---------- 压缩器 ----------

class ToolResultCompressor:
    """工具结果压缩器 — 根据 tool 类型智能裁剪输出。"""

    def __init__(self) -> None:
        self._limits: dict[str, int] = {}

    def set_tool_limit(self, tool_name: str, max_chars: int) -> None:
        self._limits[tool_name] = max_chars

    def compress(self, tool_name: str, result: dict[str, Any]) -> str:
        """将工具结果压缩为适合送入 LLM 的字符串。"""
        # 失败结果直接序列化，不压缩
        if not result.get("success", True):
            return json.dumps(result, ensure_ascii=False)

        max_chars = self._limits.get(
            tool_name, MAX_RESULT_CHARS.get(tool_name, DEFAULT_MAX_CHARS)
        )

        handler = {
            "read_file": self._compress_file,
            "list_dir": self._compress_list,
            "grep": self._compress_grep,
            "execute_command": self._compress_shell,
        }.get(tool_name, self._compress_generic)

        compressed = handler(result, max_chars)
        return compressed

    # ---- 具体压缩策略 ----

    def _compress_file(self, result: dict, max_chars: int) -> str:
        """文件内容：过长时保留首尾，中间标注省略。"""
        content = result.get("content", "")
        path = result.get("path", "")
        total_lines = content.count("\n") + 1

        if len(content) <= max_chars:
            result["content"] = content
            result["total_lines"] = total_lines
            return json.dumps(result, ensure_ascii=False)

        # 超长：head + tail + 省略标记
        lines = content.split("\n")
        head = lines[:HEAD_LINES]
        tail = lines[-TAIL_LINES:] if len(lines) > HEAD_LINES + TAIL_LINES else []

        truncated = "\n".join(head)
        if tail:
            truncated += f"\n... 省略 {total_lines - HEAD_LINES - TAIL_LINES} 行 ...\n"
            truncated += "\n".join(tail)

        result["content"] = truncated
        result["total_lines"] = total_lines
        result["truncated"] = True
        return json.dumps(result, ensure_ascii=False)

    def _compress_list(self, result: dict, max_chars: int) -> str:
        """目录列表：过长时截断并标注总数。"""
        entries = result.get("entries", [])
        total = len(entries)

        # 先尝试完整序列化
        full = json.dumps(result, ensure_ascii=False)
        if len(full) <= max_chars:
            return full

        # 截断条目
        result["entries"] = entries[:50]
        result["total_entries"] = total
        result["truncated"] = True
        return json.dumps(result, ensure_ascii=False)

    def _compress_grep(self, result: dict, max_chars: int) -> str:
        """搜索结果：过长时保留首尾匹配，标注总数。"""
        matches = result.get("matches", [])
        total = len(matches)

        full = json.dumps(result, ensure_ascii=False)
        if len(full) <= max_chars:
            return full

        # 保留前 20 条 + 总数标注
        result["matches"] = matches[:20]
        result["total_matches"] = total
        result["truncated"] = True
        return json.dumps(result, ensure_ascii=False)

    def _compress_shell(self, result: dict, max_chars: int) -> str:
        """Shell 输出：过长时保留首尾行。"""
        output = result.get("output", "")

        if len(output) <= max_chars:
            return json.dumps(result, ensure_ascii=False)

        lines = output.split("\n")
        head = lines[:HEAD_LINES]
        tail = lines[-TAIL_LINES:] if len(lines) > HEAD_LINES + TAIL_LINES else []

        truncated = "\n".join(head)
        if tail:
            truncated += f"\n... 省略 {len(lines) - HEAD_LINES - TAIL_LINES} 行 ...\n"
            truncated += "\n".join(tail)

        result["output"] = truncated
        result["truncated"] = True
        return json.dumps(result, ensure_ascii=False)

    def _compress_generic(self, result: dict, max_chars: int) -> str:
        """通用压缩：JSON 序列化后截断。"""
        text = json.dumps(result, ensure_ascii=False)
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n... [截断]"
