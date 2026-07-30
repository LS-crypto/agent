"""按 Provider 解析 API Key（DeepSeek + MiniMax 开放平台）。"""

from __future__ import annotations

import os

from core.config import (
    get_api_key_env_for_provider,
    get_provider_for_model,
)
from server.auth.dependencies import AuthUser
from server.repositories.user_secrets import (
    PROVIDER_DEEPSEEK,
    PROVIDER_MINIMAX,
    UserSecretsRepository,
)


class MissingApiKeyError(PermissionError):
    """普通用户未配置 BYOK。"""


# provider → 默认回退 provider（api_key_service 拿不到 key 时降级目标）
# 当前统一回退到 deepseek, 保持现有的 deepseek-chat 默认模型可用性。
_FALLBACK_PROVIDER = PROVIDER_DEEPSEEK


class ApiKeyService:
    def __init__(self, secrets: UserSecretsRepository | None = None) -> None:
        self._secrets = secrets or UserSecretsRepository()

    def _provider_for(self, model_id: str | None) -> str:
        """根据 model_id 选择 provider；缺省时使用 deepseek。"""
        return get_provider_for_model(model_id) if model_id else _FALLBACK_PROVIDER

    def _resolve_key_for_provider(self, user: AuthUser, provider: str) -> str | None:
        """管理员优先读平台 Key；普通用户读 BYOK。"""
        if user.role == "admin":
            env_name = get_api_key_env_for_provider(provider)
            platform = os.getenv(env_name, "").strip()
            if platform:
                return platform
        return self._secrets.get_plaintext(user.id, provider)

    def resolve_for_user(
        self, user: AuthUser, model_id: str | None = None
    ) -> str | None:
        """按 model_id 对应的 provider 取 Key；缺省走 deepseek。

        注意：模型被路由到其它 provider 但用户没有该 provider 的 key 时，**不会**
        自动回退到 deepseek（避免错向第三方 base_url 发送请求）。
        """
        provider = self._provider_for(model_id)
        return self._resolve_key_for_provider(user, provider)

    def require_for_user(self, user: AuthUser, model_id: str | None = None) -> str:
        """取模型对应的 API Key；缺失则抛友好错误（管理员提示配环境变量）。"""
        provider = self._provider_for(model_id)
        key = self._resolve_key_for_provider(user, provider)
        if not key:
            env_name = get_api_key_env_for_provider(provider)
            label = "DeepSeek" if provider == PROVIDER_DEEPSEEK else "MiniMax"
            if user.role == "admin":
                raise MissingApiKeyError(
                    f"管理员未配置平台 {env_name}（{label} 模型）"
                )
            raise MissingApiKeyError(
                f"请先在设置中保存你的 {label} API Key"
            )
        return key

    def status_for_provider(self, user: AuthUser, provider: str) -> dict:
        """组装单个 provider 的状态（含管理员平台 Key 检测）。"""
        if user.role == "admin":
            env_name = get_api_key_env_for_provider(provider)
            platform = os.getenv(env_name, "").strip()
            user_key = self._secrets.get_status(user.id, provider)
            configured = bool(platform) or user_key["configured"]
            hint = user_key.get("hint")
            if platform and not hint:
                hint = f"平台 Key（{env_name}）"
            return {
                "configured": configured,
                "hint": hint,
                "uses_platform_key": bool(platform),
                "updated_at": user_key.get("updated_at"),
                "provider": provider,
            }
        data = self._secrets.get_status(user.id, provider)
        data["uses_platform_key"] = False
        data["provider"] = provider
        return data

    def status_for_user(
        self, user: AuthUser, model_id: str | None = None
    ) -> dict:
        """返回当前模型所用 provider 的 API Key 状态。"""
        provider = self._provider_for(model_id)
        return self.status_for_provider(user, provider)
