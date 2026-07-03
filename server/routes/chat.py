"""聊天 SSE 路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from server.repositories.sessions import SessionRepository
from server.schemas import ChatConfirmRequest, ChatRequest
from server.services.agent_service import AgentService

router = APIRouter(prefix="/chat", tags=["chat"])
_repo = SessionRepository()
_service = AgentService(_repo)


@router.post("/confirm")
def chat_confirm(body: ChatConfirmRequest) -> dict[str, bool]:
    try:
        _repo.get(body.session_id, body.user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ok = _service.resolve_confirmation(
        body.user_id,
        body.session_id,
        body.confirmation_id,
        body.allowed,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="确认请求不存在或已过期")
    return {"ok": True}


@router.post("")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    try:
        _repo.get(body.session_id, body.user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StreamingResponse(
        _service.stream_chat(
            body.user_id,
            body.session_id,
            body.message,
            model=body.model,
            permission=body.permission,
            enable_routing=body.enable_routing,
            enable_compression=body.enable_compression,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
