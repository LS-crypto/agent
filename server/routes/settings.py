"""用户 API Key 设置（BYOK）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from server.auth.dependencies import AuthUser, get_current_user
from server.repositories.user_secrets import PROVIDER_DASHSCOPE, UserSecretsRepository
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
def get_api_key_status(user: AuthUser = Depends(get_current_user)) -> ApiKeyStatusResponse:
    data = _key_service.status_for_user(user)
    return ApiKeyStatusResponse(**data)


@router.put("/api-key")
def save_api_key(
    body: ApiKeySaveRequest,
    user: AuthUser = Depends(get_current_user),
) -> ApiKeyStatusResponse:
    key = body.api_key.strip()
    if len(key) < 8:
        raise HTTPException(status_code=400, detail="API Key 格式无效")
    if not key.startswith("sk-"):
        raise HTTPException(
            status_code=400,
            detail="请填写阿里云百炼 DashScope API Key（以 sk- 开头）",
        )
    _secrets.upsert(user.id, PROVIDER_DASHSCOPE, key)
    db_user = _users.get_by_id(user.id)
    if db_user:
        sync_user(db_user, _secrets)
    data = _key_service.status_for_user(user)
    return ApiKeyStatusResponse(**data)


@router.delete("/api-key")
def delete_api_key(user: AuthUser = Depends(get_current_user)) -> ApiKeyStatusResponse:
    _secrets.delete(user.id, PROVIDER_DASHSCOPE)
    db_user = _users.get_by_id(user.id)
    if db_user:
        sync_user(db_user, _secrets)
    data = _key_service.status_for_user(user)
    return ApiKeyStatusResponse(**data)
