"""启动时确保管理员账号存在。"""

from __future__ import annotations

import os

from core.agent.console import step
from server.repositories.users import UserRepository


def ensure_admin_account() -> None:
    """若配置了 ADMIN_EMAIL / ADMIN_PASSWORD，则创建或提升为管理员。"""
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not email or not password:
        return

    repo = UserRepository()
    existing = repo.get_by_email(email)
    if existing is None:
        try:
            user = repo.create(email, password, role="admin")
            step("管理员账号", f"已创建 {user['email']}")
        except ValueError as exc:
            step("管理员账号", f"创建失败: {exc}")
        return

    if existing["role"] != "admin":
        repo.set_role(existing["id"], "admin")
        step("管理员账号", f"已将 {email} 提升为管理员")
    else:
        step("管理员账号", f"已就绪 {email}")
