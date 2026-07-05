"""主管后台 API（简易版）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from server.auth.dependencies import AuthUser, require_admin
from server.repositories.sessions import SessionRepository
from server.repositories.user_secrets import UserSecretsRepository
from server.repositories.users import UserRepository
from server.schemas import AdminBanRequest, AdminUserSummary
from server.services.admin_mirror import rebuild_index, sync_user
from server.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/admin", tags=["admin"])
_users = UserRepository()
_sessions = SessionRepository()
_secrets = UserSecretsRepository()
_key_service = ApiKeyService(_secrets)


def _summarize(user: dict) -> AdminUserSummary:
    key_status = _key_service.status_for_user(
        AuthUser(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            status=user["status"],
        )
    )
    session_count = len(_sessions.list_by_user(user["id"]))
    return AdminUserSummary(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        status=user["status"],
        created_at=user.get("created_at"),
        last_login_at=user.get("last_login_at"),
        has_api_key=bool(key_status.get("configured")),
        session_count=session_count,
    )


@router.get("/users")
def list_users(_admin: AuthUser = Depends(require_admin)) -> dict:
    users = [_summarize(u) for u in _users.list_all()]
    return {"users": users, "total": len(users)}


@router.get("/users/{user_id}")
def get_user(user_id: str, _admin: AuthUser = Depends(require_admin)) -> dict:
    user = _users.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    sessions = _sessions.list_by_user(user_id)
    return {"user": _summarize(user), "sessions": sessions}


@router.post("/users/{user_id}/status")
def set_user_status(
    user_id: str,
    body: AdminBanRequest,
    _admin: AuthUser = Depends(require_admin),
) -> dict:
    try:
        updated = _users.set_status(user_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    sync_user(updated, _secrets)
    return {"ok": True, "user": _summarize(updated)}


@router.get("/stats")
def admin_stats(_admin: AuthUser = Depends(require_admin)) -> dict:
    rows = rebuild_index()
    return {
        "total_users": len(rows),
        "active_users": sum(1 for r in rows if r.get("status") == "active"),
        "banned_users": sum(1 for r in rows if r.get("status") == "banned"),
        "with_api_key": sum(1 for r in rows if r.get("has_api_key")),
        "mirror_dir": "runtime/admin/users",
    }
