"""会话 CRUD 路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from server.repositories.sessions import SessionRepository
from server.schemas import SessionCreateRequest, SessionModelRequest, SessionRenameRequest

router = APIRouter(prefix="/sessions", tags=["sessions"])
_repo = SessionRepository()


@router.get("")
def list_sessions(user_id: str = Query(default="default", min_length=1)) -> list[dict]:
    return _repo.list_by_user(user_id)


@router.post("")
def create_session(body: SessionCreateRequest) -> dict:
    return _repo.create(body.user_id, body.title, model=body.model, permission=body.permission)


@router.get("/{session_id}")
def get_session(
    session_id: str,
    user_id: str = Query(default="default", min_length=1),
) -> dict:
    try:
        return _repo.get(session_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{session_id}")
def rename_session(
    session_id: str,
    body: SessionRenameRequest,
    user_id: str = Query(default="default", min_length=1),
) -> dict:
    try:
        return _repo.rename(session_id, user_id, body.title)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{session_id}/model")
def set_session_model(
    session_id: str,
    body: SessionModelRequest,
    user_id: str = Query(default="default", min_length=1),
) -> dict:
    try:
        return _repo.set_model(session_id, user_id, body.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{session_id}/reset")
def reset_session(
    session_id: str,
    user_id: str = Query(default="default", min_length=1),
) -> dict:
    try:
        return _repo.reset(session_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    user_id: str = Query(default="default", min_length=1),
) -> dict:
    try:
        _repo.delete(session_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "session_id": session_id}
