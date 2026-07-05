"""聊天 SSE 路由。"""



from __future__ import annotations



from fastapi import APIRouter, Depends, HTTPException

from fastapi.responses import StreamingResponse



from server.auth.dependencies import AuthUser, get_current_user
from server.repositories.sessions import SessionRepository
from server.schemas import ChatConfirmRequest, ChatRequest
from server.services.agent_service import AgentService
from server.services.api_key_service import ApiKeyService, MissingApiKeyError
from server.services.access_control import ConcurrencyLimitError
from server.services.model_policy import ModelNotAllowedError, resolve_model_for_role



router = APIRouter(prefix="/chat", tags=["chat"])

_repo = SessionRepository()
_service = AgentService(_repo)
_key_service = ApiKeyService()





@router.post("/confirm")

def chat_confirm(

    body: ChatConfirmRequest,

    user: AuthUser = Depends(get_current_user),

) -> dict[str, bool]:

    try:

        _repo.get(body.session_id, user.id)

    except KeyError as exc:

        raise HTTPException(status_code=404, detail=str(exc)) from exc



    ok = _service.resolve_confirmation(

        user.id,

        body.session_id,

        body.confirmation_id,

        body.allowed,

    )

    if not ok:

        raise HTTPException(status_code=404, detail="确认请求不存在或已过期")

    return {"ok": True}





@router.post("")

async def chat_stream(
    body: ChatRequest,
    user: AuthUser = Depends(get_current_user),
) -> StreamingResponse:
    try:
        _repo.get(body.session_id, user.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        _key_service.require_for_user(user)
    except MissingApiKeyError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        resolve_model_for_role(user.role, body.model)
    except ModelNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        stream = _service.stream_chat(
            user,
            body.session_id,
            body.message,

            model=body.model,

            permission=body.permission,

            enable_routing=body.enable_routing,

            enable_compression=body.enable_compression,
        )
    except ConcurrencyLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


