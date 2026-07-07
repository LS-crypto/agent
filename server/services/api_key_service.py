"""解析对话所需的 DashScope API Key。"""

from __future__ import annotations

import os

from server.auth.dependencies import AuthUser
from server.repositories.user_secrets import PROVIDER_DASHSCOPE, UserSecretsRepository


class MissingApiKeyError(PermissionError):
    """普通用户未配置 BYOK。"""


class ApiKeyService:
    def __init__(self, secrets: UserSecretsRepository | None = None) -> None:
        self._secrets = secrets or UserSecretsRepository()

    def resolve_for_user(self, user: AuthUser) -> str | None:
        if user.role == "admin":
            platform = os.getenv("DASHSCOPE_API_KEY", "").strip()
            if platform:
                return platform
        return self._secrets.get_plaintext(user.id, PROVIDER_DASHSCOPE)

    def require_for_user(self, user: AuthUser) -> str:
        key = self.resolve_for_user(user)
        if not key:
            if user.role == "admin":
                raise MissingApiKeyError("管理员未配置平台 DASHSCOPE_API_KEY")
            raise MissingApiKeyError("请先在设置中保存你的 DashScope API Key")
        return key

    def status_for_user(self, user: AuthUser) -> dict:
        if user.role == "admin":
            platform = bool(os.getenv("DASHSCOPE_API_KEY", "").strip())
            user_key = self._secrets.get_status(user.id, PROVIDER_DASHSCOPE)
            configured = platform or user_key["configured"]
            hint = user_key["hint"]
            if platform and not hint:
                hint = "平台 Key（环境变量）"
            return {
                "configured": configured,
                "hint": hint,
                "uses_platform_key": platform,
                "updated_at": user_key.get("updated_at"),
            }
        return {
            **self._secrets.get_status(user.id, PROVIDER_DASHSCOPE),
            "uses_platform_key": False,
        }
