"""会话 CRUD 路由。"""



from __future__ import annotations



from fastapi import APIRouter, Depends, HTTPException



from server.auth.dependencies import AuthUser, get_current_user
from server.repositories.sessions import SessionRepository
from server.schemas import SessionCreateRequest, SessionModelRequest, SessionRenameRequest, RollbackLastTurnResponse
from server.services.model_policy import ModelNotAllowedError, resolve_model_for_role
from server.services.agent_service import cancel_active_chat_turn
from core.agent.multimodal import extract_images, extract_plain_text



router = APIRouter(prefix="/sessions", tags=["sessions"])

_repo = SessionRepository()





@router.get("")

def list_sessions(user: AuthUser = Depends(get_current_user)) -> list[dict]:

    return _repo.list_by_user(user.id)





@router.post("")

def create_session(

    body: SessionCreateRequest,

    user: AuthUser = Depends(get_current_user),

) -> dict:
    try:
        model = resolve_model_for_role(user.role, body.model)
    except ModelNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _repo.create(
        user.id,
        body.title,
        model=model,
        permission=body.permission,
    )





@router.get("/{session_id}")

def get_session(

    session_id: str,

    user: AuthUser = Depends(get_current_user),

) -> dict:

    try:

        return _repo.get(session_id, user.id)

    except KeyError as exc:

        raise HTTPException(status_code=404, detail=str(exc)) from exc





@router.patch("/{session_id}")

def rename_session(

    session_id: str,

    body: SessionRenameRequest,

    user: AuthUser = Depends(get_current_user),

) -> dict:

    try:

        return _repo.rename(session_id, user.id, body.title)

    except KeyError as exc:

        raise HTTPException(status_code=404, detail=str(exc)) from exc





@router.patch("/{session_id}/model")

def set_session_model(

    session_id: str,

    body: SessionModelRequest,

    user: AuthUser = Depends(get_current_user),

) -> dict:
    try:
        model = resolve_model_for_role(user.role, body.model)
    except ModelNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    try:
        return _repo.set_model(session_id, user.id, model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc





@router.post("/{session_id}/rollback-last-turn")

def rollback_last_turn(

    session_id: str,

    user: AuthUser = Depends(get_current_user),

) -> RollbackLastTurnResponse:

    try:

        cancel_active_chat_turn(session_id)

        session, withdrawn = _repo.rollback_last_turn(session_id, user.id)

    except ValueError as exc:

        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except KeyError as exc:

        raise HTTPException(status_code=404, detail=str(exc)) from exc

    content = withdrawn.get("content")

    return RollbackLastTurnResponse(

        message=extract_plain_text(content),

        images=extract_images(content),

        session=session,

    )





@router.post("/{session_id}/reset")

def reset_session(

    session_id: str,

    user: AuthUser = Depends(get_current_user),

) -> dict:

    try:

        return _repo.reset(session_id, user.id)

    except KeyError as exc:

        raise HTTPException(status_code=404, detail=str(exc)) from exc





@router.delete("/{session_id}")

def delete_session(

    session_id: str,

    user: AuthUser = Depends(get_current_user),

) -> dict:

    try:

        _repo.delete(session_id, user.id)

    except KeyError as exc:

        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"ok": True, "session_id": session_id}


