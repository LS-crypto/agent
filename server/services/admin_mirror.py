"""将用户摘要镜像到 runtime/admin/，便于本地文件夹监控。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.user.paths import admin_dir
from server.repositories.user_secrets import PROVIDER_DASHSCOPE, UserSecretsRepository


def _users_dir() -> Path:
    path = admin_dir() / "users"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _user_record(user: dict[str, Any], *, has_api_key: bool) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "status": user["status"],
        "created_at": user.get("created_at"),
        "last_login_at": user.get("last_login_at"),
        "has_api_key": has_api_key,
        "mirrored_at": _now(),
    }


def sync_user(user: dict[str, Any], secrets: UserSecretsRepository | None = None) -> None:
    """写入 runtime/admin/users/{id}.json 并刷新 index.json。"""
    repo = secrets or UserSecretsRepository()
    has_key = repo.has_secret(user["id"], PROVIDER_DASHSCOPE)
    record = _user_record(user, has_api_key=has_key)
    users_path = _users_dir()
    (users_path / f"{user['id']}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    rebuild_index()


def rebuild_index() -> list[dict[str, Any]]:
    users_path = _users_dir()
    rows: list[dict[str, Any]] = []
    for path in sorted(users_path.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    summary = {
        "updated_at": _now(),
        "total": len(rows),
        "active": sum(1 for r in rows if r.get("status") == "active"),
        "banned": sum(1 for r in rows if r.get("status") == "banned"),
        "with_api_key": sum(1 for r in rows if r.get("has_api_key")),
        "users": rows,
    }
    (users_path / "index.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return rows
