"""封装 CodingAgent，供 HTTP/SSE 调用。"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

from core.agent.coding_agent import CodingAgent
from core.agent.confirmation import get_confirmation_manager
from core.agent.multimodal import (
    ChatImageError,
    build_user_content,
    extract_text,
    resolve_vision_model,
    validate_image_list,
)
from server.auth.dependencies import AuthUser
from server.repositories.sessions import SessionRepository
from server.services.api_key_service import ApiKeyService, MissingApiKeyError
from server.services.access_control import ChatConcurrencyGuard, ConcurrencyLimitError
from server.services.model_policy import ModelNotAllowedError, resolve_model_for_role


def _sse_line(record: dict[str, Any]) -> str:
    return f"data: {json.dumps(record, ensure_ascii=False)}\n\n"


def _derive_title(message: str, current_title: str) -> str | None:
    if current_title != "新会话":
        return None
    text = message.strip().replace("\n", " ")
    if not text:
        return None
    return text[:40] + ("…" if len(text) > 40 else "")


def _queue_get(
    event_queue: queue.Queue[dict[str, Any] | None],
    timeout: float,
) -> dict[str, Any] | None:
    """带心跳占位，避免长工具执行时 SSE 连接被中间层断开。"""
    try:
        return event_queue.get(timeout=timeout)
    except queue.Empty:
        from datetime import datetime

        return {
            "event": "heartbeat",
            "time": datetime.now().isoformat(timespec="seconds"),
        }


class AgentService:
    def __init__(
        self,
        repo: SessionRepository | None = None,
        key_service: ApiKeyService | None = None,
    ) -> None:
        self.repo = repo or SessionRepository()
        self.confirmations = get_confirmation_manager()
        self.key_service = key_service or ApiKeyService()

    def _build_agent(
        self,
        user_id: str,
        messages: list[dict[str, Any]],
        *,
        enable_compression: bool = True,
        api_key: str | None = None,
    ) -> CodingAgent:
        agent = CodingAgent(
            user_id=user_id,
            resume=False,
            verbose=False,
            persist_json=False,
            messages=messages,
            api_key=api_key,
        )
        agent.loop.enable_compression = enable_compression
        return agent

    async def stream_chat(
        self,
        user: AuthUser,
        session_id: str,
        message: str,
        *,
        images: list[str] | None = None,
        model: str | None = None,
        permission: str | None = None,
        enable_routing: bool | None = None,
        enable_compression: bool = True,
    ) -> AsyncIterator[str]:
        user_id = user.id
        api_key = self.key_service.require_for_user(user)
        session = self.repo.get(session_id, user_id)
        try:
            validated_images = validate_image_list(images)
        except ChatImageError as exc:
            yield _sse_line({"event": "error", "message": str(exc)})
            return

        user_content = build_user_content(message, validated_images)
        display_text = extract_text(user_content)

        try:
            chosen = resolve_model_for_role(
                user.role,
                model or session.get("model"),
            )
            if validated_images:
                chosen = resolve_vision_model(chosen)
                chosen = resolve_model_for_role(user.role, chosen)
                enable_routing = False
        except ChatImageError as exc:
            yield _sse_line({"event": "error", "message": str(exc)})
            return
        except ModelNotAllowedError as exc:
            yield _sse_line({"event": "error", "message": str(exc)})
            return
        perm = permission or session.get("permission") or "balanced"
        derived_title = _derive_title(display_text, session["title"])
        session = self.repo.append_user_message(
            session_id,
            user_id,
            user_content,
            title=derived_title,
            model=chosen,
        )
        event_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
        last_checkpoint = [0.0]
        agent: CodingAgent | None = None

        try:
            guard = ChatConcurrencyGuard(user_id)
            guard.__enter__()
        except ConcurrencyLimitError as exc:
            yield _sse_line({"event": "error", "message": str(exc)})
            return

        def on_event(record: dict[str, Any]) -> None:
            event_queue.put(record)
            if agent is None:
                return
            ev = record.get("event")
            if ev not in ("tool_result", "assistant_reply"):
                return
            now = time.monotonic()
            if ev != "assistant_reply" and now - last_checkpoint[0] < 2.0:
                return
            last_checkpoint[0] = now
            try:
                self.repo.update_messages(
                    session_id,
                    user_id,
                    agent.session.messages,
                    model=chosen,
                )
            except Exception:
                pass

        def confirm_handler(tool: str, args: dict[str, Any]) -> bool:
            return self.confirmations.request(
                session_id=session_id,
                user_id=user_id,
                tool=tool,
                args=args,
                on_event=on_event,
            )

        def run_agent() -> None:
            nonlocal agent
            try:
                agent = self._build_agent(
                    user_id,
                    session["messages"],
                    enable_compression=enable_compression,
                    api_key=api_key,
                )
                reply = agent.chat(
                    message,
                    on_event=on_event,
                    confirm_handler=confirm_handler,
                    session_id=session_id,
                    model=chosen,
                    permission=perm,
                    enable_routing=enable_routing,
                    user_message_persisted=True,
                    images=validated_images or None,
                )
                title = _derive_title(display_text, session["title"])
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
                guard.__exit__(None, None, None)
                event_queue.put(None)

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        loop = asyncio.get_running_loop()
        while True:
            record = await loop.run_in_executor(None, _queue_get, event_queue, 20.0)
            if record is None:
                break
            if record.get("event") == "heartbeat":
                yield _sse_line(record)
                continue
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
