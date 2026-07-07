"""用户工作区磁盘配额（阶段 L）。"""

from __future__ import annotations

import os
from pathlib import Path

from core.user.paths import ensure_user_dirs, workspace_projects
from core.user.workspace_binding import load_binding

DEFAULT_QUOTA_BYTES = 100 * 1024 * 1024


def get_quota_limit_bytes() -> int | None:
    """返回配额上限；None 表示不限制（USER_WORKSPACE_QUOTA_BYTES=0）。"""
    raw = os.getenv("USER_WORKSPACE_QUOTA_BYTES", str(DEFAULT_QUOTA_BYTES)).strip()
    if not raw or raw == "0":
        return None
    return max(0, int(raw))


def workspace_usage_bytes(root: Path) -> int:
    """统计 projects/ 目录内所有普通文件占用。"""
    total = 0
    if not root.is_dir():
        return 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                if fp.is_symlink():
                    continue
                if fp.is_file():
                    total += fp.stat().st_size
            except OSError:
                continue
    return total


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} PB"


def quota_summary(user_id: str) -> dict:
    """供 API 展示：已用 / 上限 / 剩余。"""
    ensure_user_dirs(user_id)
    root = workspace_projects(user_id).resolve()
    used = workspace_usage_bytes(root)
    if not _quota_applies(user_id):
        return {
            "quota_bytes": None,
            "quota_size": None,
            "quota_remaining_bytes": None,
            "quota_remaining_size": None,
            "quota_percent_used": None,
        }
    limit = get_quota_limit_bytes()
    if limit is None:
        return {
            "quota_bytes": None,
            "quota_size": None,
            "quota_remaining_bytes": None,
            "quota_remaining_size": None,
            "quota_percent_used": None,
        }
    remaining = max(0, limit - used)
    return {
        "quota_bytes": limit,
        "quota_size": _human_bytes(limit),
        "quota_remaining_bytes": remaining,
        "quota_remaining_size": _human_bytes(remaining),
        "quota_percent_used": round(used / limit * 100, 1) if limit else 0.0,
    }


def _quota_applies(user_id: str) -> bool:
    if get_quota_limit_bytes() is None:
        return False
    return load_binding(user_id).get("mode") != "local"


def check_workspace_quota(
    user_id: str,
    *,
    extra_bytes: int,
    replace_path: Path | None = None,
) -> dict | None:
    """若超出配额返回工具错误 dict，否则 None。"""
    if not _quota_applies(user_id):
        return None
    limit = get_quota_limit_bytes()
    assert limit is not None

    ensure_user_dirs(user_id)
    root = workspace_projects(user_id).resolve()
    used = workspace_usage_bytes(root)

    if replace_path is not None and replace_path.is_file():
        try:
            used -= replace_path.stat().st_size
        except OSError:
            pass

    projected = used + extra_bytes
    if projected <= limit:
        return None

    return {
        "success": False,
        "error": (
            f"工作区空间不足（已用 {_human_bytes(used)}，"
            f"上限 {_human_bytes(limit)}），请删除文件后再写入"
        ),
        "policy": "workspace_quota",
        "used_bytes": used,
        "quota_bytes": limit,
        "projected_bytes": projected,
    }
