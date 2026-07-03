"""系统信息工具（纯 Python，无 Shell）— 磁盘、工作区、运行环境。"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

from core.tools.registry import ToolRegistry
from core.tools.sandbox import WorkspaceSandbox


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"


class SystemTools:
    def __init__(self, user_id: str) -> None:
        self.sandbox = WorkspaceSandbox(user_id)

    def get_disk_usage(self, path: str = ".") -> dict:
        """沙箱所在磁盘的空间使用情况（total/used/free）。"""
        try:
            resolved = self.sandbox.resolve(path)
            if isinstance(resolved, dict):
                return resolved
            target = resolved if resolved.is_dir() else resolved.parent
            usage = shutil.disk_usage(target)
            return {
                "success": True,
                "path": str(target),
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "total": _human_bytes(usage.total),
                "used": _human_bytes(usage.used),
                "free": _human_bytes(usage.free),
                "percent_used": round(usage.used / usage.total * 100, 1)
                if usage.total
                else 0,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_workspace_stats(self) -> dict:
        """统计沙箱项目目录：文件数、总大小、最大文件。"""
        root = self.sandbox.root.resolve()
        file_count = 0
        total_size = 0
        largest: tuple[int, str] = (0, "")

        try:
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    fp = Path(dirpath) / name
                    try:
                        if fp.is_symlink():
                            continue
                        size = fp.stat().st_size
                    except OSError:
                        continue
                    file_count += 1
                    total_size += size
                    if size > largest[0]:
                        rel = str(fp.relative_to(root))
                        largest = (size, rel)

            return {
                "success": True,
                "root": str(root),
                "file_count": file_count,
                "total_bytes": total_size,
                "total_size": _human_bytes(total_size),
                "largest_file": largest[1] or None,
                "largest_bytes": largest[0],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_env_info(self) -> dict:
        """运行环境摘要（不含密钥）。"""
        return {
            "success": True,
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "cwd": str(self.sandbox.root.resolve()),
            "user_id": self.sandbox.user_id,
        }


def register_system_tools(registry: ToolRegistry, user_id: str) -> None:
    tools = SystemTools(user_id)

    registry.register(
        "get_disk_usage",
        "查看沙箱所在磁盘的存储空间（总量/已用/可用）。无需 Shell，安全只读。",
        {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "沙箱内相对路径，默认 . 表示项目根",
                },
            },
        },
        tools.get_disk_usage,
    )
    registry.register(
        "get_workspace_stats",
        "统计沙箱项目目录的文件数量与占用空间，找出最大文件。",
        {"type": "object", "properties": {}},
        lambda **_: tools.get_workspace_stats(),
    )
    registry.register(
        "get_env_info",
        "获取 Python 版本、平台与沙箱路径（不含环境变量密钥）。",
        {"type": "object", "properties": {}},
        lambda **_: tools.get_env_info(),
    )
