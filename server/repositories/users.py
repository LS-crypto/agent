"""用户 CRUD。"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from server.auth.passwords import hash_password, verify_password
from server.db.database import get_connection
from server.services.user_provision import provision_user_storage

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "role": row["role"],
        "status": row["status"],
        "created_at": row["created_at"],
        "last_login_at": row.get("last_login_at"),
        "display_name": row.get("display_name"),
        "avatar": row.get("avatar"),
    }


class UserRepository:
    def create(self, email: str, password: str, *, role: str = "user") -> dict[str, Any]:
        normalized = _normalize_email(email)
        if not _EMAIL_RE.match(normalized):
            raise ValueError("邮箱格式无效")
        if len(password) < 8:
            raise ValueError("密码至少 8 位")

        user_id = str(uuid.uuid4())
        now = _now()
        password_hash = hash_password(password)

        with get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users (
                        id, email, password_hash, role, status, created_at, last_login_at
                    )
                    VALUES (?, ?, ?, ?, 'active', ?, NULL)
                    """,
                    (user_id, normalized, password_hash, role, now),
                )
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise ValueError("该邮箱已注册") from exc
                raise

        user = self.get_by_id(user_id)
        assert user is not None
        provision_user_storage(user_id, email=normalized)
        return user

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        normalized = _normalize_email(email)
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, email, password_hash, role, status, created_at, last_login_at
                FROM users
                WHERE email = ?
                """,
                (normalized,),
            ).fetchone()
        if row is None:
            return None
        user = dict(row)
        if not verify_password(password, user["password_hash"]):
            return None
        if user["status"] == "banned":
            raise PermissionError("账号已被禁用")
        self.touch_last_login(user["id"])
        refreshed = self.get_by_id(user["id"])
        return refreshed

    def touch_last_login(self, user_id: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?",
                (_now(), user_id),
            )

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, email, role, status, created_at, last_login_at,
                       display_name, avatar
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return _public_user(dict(row))

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        normalized = _normalize_email(email)
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, email, role, status, created_at, last_login_at,
                       display_name, avatar
                FROM users
                WHERE email = ?
                """,
                (normalized,),
            ).fetchone()
        if row is None:
            return None
        return _public_user(dict(row))

    def count(self) -> int:
        with get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        return int(row["c"]) if row else 0

    def list_all(self) -> list[dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, email, role, status, created_at, last_login_at,
                       display_name, avatar
                FROM users
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [_public_user(dict(row)) for row in rows]

    def set_status(self, user_id: str, status: str) -> dict[str, Any] | None:
        if status not in ("active", "banned"):
            raise ValueError("无效的状态")
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET status = ? WHERE id = ?",
                (status, user_id),
            )
        return self.get_by_id(user_id)

    def set_role(self, user_id: str, role: str) -> dict[str, Any] | None:
        if role not in ("user", "admin"):
            raise ValueError("无效的角色")
        with get_connection() as conn:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        return self.get_by_id(user_id)

    def set_password(self, user_id: str, password: str) -> None:
        if len(password) < 8:
            raise ValueError("密码至少 8 位")
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(password), user_id),
            )

    def update_profile(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        avatar: str | None = None,
    ) -> dict[str, Any] | None:
        updates: list[str] = []
        params: list[Any] = []
        if display_name is not None:
            name = display_name.strip()
            if len(name) < 2 or len(name) > 32:
                raise ValueError("显示名称需 2–32 个字符")
            updates.append("display_name = ?")
            params.append(name)
        if avatar is not None:
            av = avatar.strip()
            if not av or len(av) > 8:
                raise ValueError("头像无效")
            updates.append("avatar = ?")
            params.append(av)
        if not updates:
            return self.get_by_id(user_id)
        params.append(user_id)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                params,
            )
        return self.get_by_id(user_id)
