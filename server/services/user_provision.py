"""用户注册时创建工作区与独立数据库。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from core.agent.console import step
from core.user.paths import (
    ensure_user_dirs,
    user_data_dir,
    user_db_path,
    workspace_projects,
)
from server.db.user_database import init_user_db, user_db_exists


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def provision_user_storage(user_id: str, *, email: str | None = None) -> dict[str, Any]:
    """为注册用户创建隔离工作区 + 独立会话数据库。"""
    ensure_user_dirs(user_id)
    data_dir = user_data_dir(user_id)
    data_dir.mkdir(parents=True, exist_ok=True)

    created_db = not user_db_exists(user_id)
    init_user_db(user_id)

    profile = {
        "user_id": user_id,
        "email": email,
        "provisioned_at": _now(),
        "workspace_projects": str(workspace_projects(user_id)),
        "sessions_db": str(user_db_path(user_id)),
    }
    profile_path = data_dir / "profile.json"
    if not profile_path.is_file():
        profile_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if created_db:
        step(
            "用户隔离",
            f"已为 {email or user_id} 创建独立库 {user_db_path(user_id).name}",
        )

    return {
        "user_id": user_id,
        "workspace_dir": str(workspace_projects(user_id).parent),
        "projects_dir": str(workspace_projects(user_id)),
        "db_path": str(user_db_path(user_id)),
        "profile_path": str(profile_path),
    }


def get_user_storage_info(user_id: str) -> dict[str, str]:
    return {
        "workspace_dir": str(workspace_projects(user_id).parent),
        "projects_dir": str(workspace_projects(user_id)),
        "db_path": str(user_db_path(user_id)),
    }
