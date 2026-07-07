"""注册 / 登录 / 当前用户。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from server.auth.dependencies import AuthUser, get_current_user
from server.auth.jwt_tokens import create_access_token
from server.repositories.users import UserRepository
from server.schemas import AuthLoginRequest, AuthRegisterRequest, AuthTokenResponse, AuthUserResponse
from server.services.access_control import RegistrationCapError, check_registration_allowed
from server.services.admin_mirror import sync_user

router = APIRouter(prefix="/auth", tags=["auth"])
_users = UserRepository()


def _token_response(user: dict) -> AuthTokenResponse:
    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
    )
    return AuthTokenResponse(
        access_token=token,
        user=AuthUserResponse(**user),
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: AuthRegisterRequest) -> AuthTokenResponse:
    try:
        check_registration_allowed(_users.count())
        user = _users.create(body.email, body.password)
    except RegistrationCapError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sync_user(user)
    return _token_response(user)


@router.post("/login")
def login(body: AuthLoginRequest) -> AuthTokenResponse:
    try:
        user = _users.authenticate(body.email, body.password)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    sync_user(user)
    return _token_response(user)


@router.get("/me")
def me(user: AuthUser = Depends(get_current_user)) -> AuthUserResponse:
    db_user = _users.get_by_id(user.id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return AuthUserResponse(**db_user)


@router.post("/logout")
def logout() -> dict[str, bool]:
    return {"ok": True}
