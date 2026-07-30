"""用户 API Key 设置（BYOK，多 Provider）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from server.auth.dependencies import AuthUser, get_current_user
from server.repositories.user_secrets import (
    KNOWN_PROVIDERS,
    PROVIDER_DEEPSEEK,
    PROVIDER_MINIMAX,
    UserSecretsRepository,
)
from server.repositories.users import UserRepository
from server.schemas import ApiKeySaveRequest, ApiKeyStatusResponse, AuthUserResponse, UserProfileUpdateRequest
from server.services.admin_mirror import sync_user
from server.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/settings", tags=["settings"])
_secrets = UserSecretsRepository()
_users = UserRepository()
_key_service = ApiKeyService(_secrets)


@router.get("/profile")
def get_profile(user: AuthUser = Depends(get_current_user)) -> AuthUserResponse:
    db_user = _users.get_by_id(user.id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return AuthUserResponse(**db_user)


@router.patch("/profile")
def update_profile(
    body: UserProfileUpdateRequest,
    user: AuthUser = Depends(get_current_user),
) -> AuthUserResponse:
    try:
        updated = _users.update_profile(
            user.id,
            display_name=body.display_name,
            avatar=body.avatar,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    sync_user(updated, _secrets)
    return AuthUserResponse(**updated)


@router.get("/api-key")
def get_api_key_status(
    provider: str = Query(default=PROVIDER_DEEPSEEK, description="Provider 标识: deepseek | minimax"),
    user: AuthUser = Depends(get_current_user),
) -> ApiKeyStatusResponse:
    """返回当前用户对指定 Provider 的 Key 配置状态。"""
    if provider not in KNOWN_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"未知 Provider: {provider}")
    data = _key_service.status_for_provider(user, provider)
    return ApiKeyStatusResponse(**data)


@router.put("/api-key")
def save_api_key(
    body: ApiKeySaveRequest,
    provider: str = Query(default=PROVIDER_DEEPSEEK),
    user: AuthUser = Depends(get_current_user),
) -> ApiKeyStatusResponse:
    if provider not in KNOWN_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"未知 Provider: {provider}")
    key = body.api_key.strip()
    if len(key) < 8:
        raise HTTPException(status_code=400, detail="API Key 格式无效")
    if provider == PROVIDER_DEEPSEEK and not key.startswith("sk-"):
        raise HTTPException(
            status_code=400,
            detail="请填写 DeepSeek API Key（以 sk- 开头）",
        )
    # MiniMax 开放平台的 Key 形态多样：JWT（ey...）或自定义 sk-api-... 都在用；
    # 仅做最小长度校验，不强制前缀以免误伤。
    if provider == PROVIDER_MINIMAX and not key.startswith(("ey", "sk-")):
        raise HTTPException(
            status_code=400,
            detail="MiniMax API Key 格式异常（应以 ey 或 sk- 开头）",
        )
    _secrets.upsert(user.id, provider, key)
    db_user = _users.get_by_id(user.id)
    if db_user:
        sync_user(db_user, _secrets)
    data = _key_service.status_for_provider(user, provider)
    return ApiKeyStatusResponse(**data)


@router.delete("/api-key")
def delete_api_key(
    provider: str = Query(default=PROVIDER_DEEPSEEK),
    user: AuthUser = Depends(get_current_user),
) -> ApiKeyStatusResponse:
    if provider not in KNOWN_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"未知 Provider: {provider}")
    _secrets.delete(user.id, provider)
    db_user = _users.get_by_id(user.id)
    if db_user:
        sync_user(db_user, _secrets)
    data = _key_service.status_for_provider(user, provider)
    return ApiKeyStatusResponse(**data)
