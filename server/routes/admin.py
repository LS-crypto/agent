"""主管后台 API。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
import queue
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from server.auth.dependencies import AuthUser, require_admin
from server.repositories.sessions import SessionRepository
from server.repositories.user_secrets import PROVIDER_DASHSCOPE, UserSecretsRepository
from server.repositories.users import UserRepository
from server.schemas import AdminBanRequest, AdminUserSummary
from server.services.activity_bus import subscribe, unsubscribe
from server.services.activity_reader import read_user_activity
from server.services.admin_mirror import rebuild_index, sync_user
from server.services.api_key_service import ApiKeyService
from server.services.user_provision import get_user_storage_info

router = APIRouter(prefix="/admin", tags=["admin"])
_users = UserRepository()
_sessions = SessionRepository()
_secrets = UserSecretsRepository()
_key_service = ApiKeyService(_secrets)


def _summarize(user: dict) -> AdminUserSummary:
    """汇总用户信息；绝不返回 API Key 明文或掩码。"""
    uid = user["id"]
    storage = get_user_storage_info(uid)
    session_count = _sessions.count_for_user(uid)
    has_key = False
    if user["role"] != "admin":
        has_key = _secrets.has_secret(uid, PROVIDER_DASHSCOPE)
    else:
        import os

        has_key = bool(os.getenv("DASHSCOPE_API_KEY", "").strip()) or _secrets.has_secret(
            uid, PROVIDER_DASHSCOPE
        )
    return AdminUserSummary(
        id=uid,
        email=user["email"],
        role=user["role"],
        status=user["status"],
        created_at=user.get("created_at"),
        last_login_at=user.get("last_login_at"),
        has_api_key=has_key,
        session_count=session_count,
        workspace_dir=storage["workspace_dir"],
        projects_dir=storage["projects_dir"],
        db_path=storage["db_path"],
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
    questions = read_user_activity(
        user_id=user_id,
        limit=50,
        events=["user_message"],
    )
    return {
        "user": _summarize(user),
        "sessions": sessions,
        "recent_questions": [
            {
                "time": q.get("time"),
                "content": q.get("content", ""),
            }
            for q in questions
        ],
    }


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


@router.get("/activity")
def admin_activity(
    _admin: AuthUser = Depends(require_admin),
    date: str | None = Query(default=None, description="YYYY-MM-DD"),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    event: str | None = Query(default=None, description="逗号分隔事件类型"),
) -> dict:
    events = [e.strip() for e in event.split(",")] if event else None
    rows = read_user_activity(
        date_str=date,
        user_id=user_id,
        limit=limit,
        events=events,
    )
    return {
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "events": rows,
        "total": len(rows),
    }


@router.get("/activity/live")
async def admin_activity_live(
    _admin: AuthUser = Depends(require_admin),
) -> StreamingResponse:
    """管理员实时活动 SSE（用户提问、工具调用等）。"""

    async def stream() -> asyncio.AsyncIterator[str]:
        q = subscribe()
        loop = asyncio.get_running_loop()
        try:
            while True:
                try:
                    record = await loop.run_in_executor(
                        None, lambda: q.get(timeout=25)
                    )
                    yield f"data: {json.dumps(record, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield 'data: {"event":"heartbeat"}\n\n'
        finally:
            unsubscribe(q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
