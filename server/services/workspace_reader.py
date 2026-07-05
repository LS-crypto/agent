"""用户工作区只读 API 服务（沙箱 projects/ 目录）。"""

from __future__ import annotations

import os
from pathlib import Path

from core.tools.filesystem import FileSystemTools
from core.tools.policy import MAX_LIST_ENTRIES, is_sensitive_path
from core.tools.sandbox import WorkspaceSandbox
from core.tools.system import SystemTools
from core.user.paths import ensure_user_dirs, workspace_projects

MAX_WORKSPACE_FILES = MAX_LIST_ENTRIES


def get_workspace_info(user_id: str) -> dict:
    """沙箱根路径 + 统计信息。"""
    ensure_user_dirs(user_id)
    root = workspace_projects(user_id).resolve()
    stats = SystemTools(user_id).get_workspace_stats()
    return {
        "root": str(root),
        "projects_dir": str(root),
        "file_count": stats.get("file_count", 0),
        "total_bytes": stats.get("total_bytes", 0),
        "total_size": stats.get("total_size", "0 B"),
        "largest_file": stats.get("largest_file"),
    }


def list_workspace_files(user_id: str, *, subpath: str = ".") -> dict:
    """递归列出沙箱内文件与目录（相对路径）。"""
    sandbox = WorkspaceSandbox(user_id)
    resolved = sandbox.resolve(subpath, check_sensitive=True)
    if isinstance(resolved, dict):
        return resolved
    if not resolved.is_dir():
        return {"success": False, "error": f"目录不存在: {subpath}"}

    root = sandbox.root.resolve()
    entries: list[dict] = []
    truncated = False

    for dirpath, dirnames, filenames in os.walk(resolved):
        current = Path(dirpath)
        rel_dir = sandbox.rel(current) if current != root else "."
        if rel_dir != ".":
            if not is_sensitive_path(rel_dir):
                entries.append({"path": rel_dir, "name": current.name, "type": "dir"})
                if len(entries) >= MAX_WORKSPACE_FILES:
                    truncated = True
                    break

        dirnames[:] = sorted(
            d for d in dirnames if not is_sensitive_path(str(current / d))
        )

        for name in sorted(filenames):
            fp = current / name
            rel = sandbox.rel(fp)
            if is_sensitive_path(rel):
                continue
            try:
                size = fp.stat().st_size if fp.is_file() and not fp.is_symlink() else 0
            except OSError:
                size = 0
            entries.append(
                {
                    "path": rel,
                    "name": name,
                    "type": "file",
                    "size": size,
                }
            )
            if len(entries) >= MAX_WORKSPACE_FILES:
                truncated = True
                break
        if truncated:
            break

    result: dict = {
        "success": True,
        "path": subpath,
        "entries": entries,
        "count": len(entries),
    }
    if truncated:
        result["truncated"] = True
    return result


def read_workspace_file(user_id: str, file_path: str) -> dict:
    """读取沙箱内文本文件。"""
    return FileSystemTools(user_id).read_file(file_path)
