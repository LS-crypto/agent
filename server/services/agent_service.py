"""封装 CodingAgent，供 HTTP/SSE 调用。"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from collections.abc import AsyncIterator, Callable
from typing import Any

from core.agent.coding_agent import CodingAgent
from core.agent.confirmation import get_confirmation_manager
from core.models.catalog import AUTO_MODEL_ID
from server.repositories.sessions import SessionRepository


def _sse_line(record: dict[str, Any]) -> str:
    return f"data: {json.dumps(record, ensure_ascii=False)}\n\n"


def _derive_title(message: str, current_title: str) -> str | None:
    if current_title != "新会话":
        return None
    text = message.strip().replace("\n", " ")
    if not text:
        return None
    return text[:40] + ("…" if len(text) > 40 else "")


class AgentService:
    def __init__(self, repo: SessionRepository | None = None) -> None:
        self.repo = repo or SessionRepository()
        self.confirmations = get_confirmation_manager()

    def _build_agent(
        self,
        user_id: str,
        messages: list[dict[str, Any]],
        *,
        enable_compression: bool = True,
    ) -> CodingAgent:
        agent = CodingAgent(
            user_id=user_id,
            resume=False,
            verbose=False,
            persist_json=False,
            messages=messages,
        )
        agent.loop.enable_compression = enable_compression
        return agent

    async def stream_chat(
        self,
        user_id: str,
        session_id: str,
        message: str,
        *,
        model: str | None = None,
        permission: str | None = None,
        enable_routing: bool | None = None,
        enable_compression: bool = True,
    ) -> AsyncIterator[str]:
        session = self.repo.get(session_id, user_id)
        chosen = model or session.get("model") or AUTO_MODEL_ID
        perm = permission or session.get("permission") or "balanced"
        event_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()

        def on_event(record: dict[str, Any]) -> None:
            event_queue.put(record)

        def confirm_handler(tool: str, args: dict[str, Any]) -> bool:
            return self.confirmations.request(
                session_id=session_id,
                user_id=user_id,
                tool=tool,
                args=args,
                on_event=on_event,
            )

        def run_agent() -> None:
            try:
                agent = self._build_agent(
                    user_id,
                    session["messages"],
                    enable_compression=enable_compression,
                )
                reply = agent.chat(
                    message,
                    on_event=on_event,
                    confirm_handler=confirm_handler,
                    session_id=session_id,
                    model=chosen,
                    permission=perm,
                    enable_routing=enable_routing,
                )
                title = _derive_title(message, session["title"])
                updated = self.repo.update_messages(
                    session_id,
                    user_id,
                    agent.session.messages,
                    title=title,
                    model=chosen,
                )
                event_queue.put(
                    {
                        "event": "done",
                        "session_id": session_id,
                        "content": reply,
                        "model": updated.get("model", chosen),
                    }
                )
            except Exception as exc:
                event_queue.put({"event": "error", "message": str(exc)})
            finally:
                event_queue.put(None)

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        loop = asyncio.get_running_loop()
        while True:
            record = await loop.run_in_executor(None, event_queue.get)
            if record is None:
                break
            yield _sse_line(record)

    def resolve_confirmation(
        self,
        user_id: str,
        session_id: str,
        confirmation_id: str,
        allowed: bool,
    ) -> bool:
        return self.confirmations.resolve(
            confirmation_id,
            user_id=user_id,
            session_id=session_id,
            allowed=allowed,
        )
