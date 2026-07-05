"""用户 API Key 设置（BYOK）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from server.auth.dependencies import AuthUser, get_current_user
from server.repositories.user_secrets import PROVIDER_DASHSCOPE, UserSecretsRepository
from server.schemas import ApiKeySaveRequest, ApiKeyStatusResponse
from server.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/settings", tags=["settings"])
_secrets = UserSecretsRepository()
_key_service = ApiKeyService(_secrets)


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
        raise HTTPException(status_code=400, detail="DashScope Key 通常以 sk- 开头")
    _secrets.upsert(user.id, PROVIDER_DASHSCOPE, key)
    data = _key_service.status_for_user(user)
    return ApiKeyStatusResponse(**data)


@router.delete("/api-key")
def delete_api_key(user: AuthUser = Depends(get_current_user)) -> ApiKeyStatusResponse:
    _secrets.delete(user.id, PROVIDER_DASHSCOPE)
    data = _key_service.status_for_user(user)
    return ApiKeyStatusResponse(**data)
