"""Human-in-the-Loop 确认管理（Web SSE）。"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.tools.policy import (
    RiskLevel,
    build_confirmation_detail,
    effective_tool_risk,
    sse_confirmation_args,
)

CONFIRMATION_TTL = 300  # 5 分钟


@dataclass
class PendingConfirmation:
    id: str
    session_id: str
    user_id: str
    tool: str
    args: dict[str, Any]
    risk: RiskLevel
    created_at: float = field(default_factory=time.time)
    event: threading.Event = field(default_factory=threading.Event)
    result: bool | None = None


class ConfirmationManager:
    def __init__(self) -> None:
        self._pending: dict[str, PendingConfirmation] = {}
        self._lock = threading.Lock()

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            cid
            for cid, p in self._pending.items()
            if now - p.created_at > CONFIRMATION_TTL
        ]
        for cid in expired:
            pending = self._pending.pop(cid, None)
            if pending and pending.result is None:
                pending.result = False
                pending.event.set()

    def request(
        self,
        *,
        session_id: str,
        user_id: str,
        tool: str,
        args: dict[str, Any],
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> bool:
        confirmation_id = str(uuid.uuid4())
        risk = effective_tool_risk(tool, args)
        detail = build_confirmation_detail(tool, args)
        pending = PendingConfirmation(
            id=confirmation_id,
            session_id=session_id,
            user_id=user_id,
            tool=tool,
            args=args,
            risk=risk,
        )

        with self._lock:
            self._cleanup_expired()
            self._pending[confirmation_id] = pending

        if on_event:
            on_event(
                {
                    "event": "confirmation_required",
                    "confirmation_id": confirmation_id,
                    "tool": tool,
                    "args": sse_confirmation_args(tool, args),
                    "risk": risk,
                    "summary": detail["summary"],
                    "explanation": detail["explanation"],
                    "impact": detail["impact"],
                    "severity": detail["severity"],
                    "permission_tier": detail["tier"],
                }
            )

        pending.event.wait(timeout=CONFIRMATION_TTL)

        with self._lock:
            self._pending.pop(confirmation_id, None)

        return pending.result is True

    def resolve(
        self,
        confirmation_id: str,
        *,
        user_id: str,
        session_id: str,
        allowed: bool,
    ) -> bool:
        with self._lock:
            self._cleanup_expired()
            pending = self._pending.get(confirmation_id)
            if pending is None:
                return False
            if pending.user_id != user_id or pending.session_id != session_id:
                return False
            if pending.result is not None:
                return False
            pending.result = allowed
            pending.event.set()
            return True


_manager = ConfirmationManager()


def get_confirmation_manager() -> ConfirmationManager:
    return _manager
