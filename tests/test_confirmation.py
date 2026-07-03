"""Human-in-the-Loop 确认与工具门禁测试。"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

from core.agent.confirmation import ConfirmationManager
from core.agent.rate_limit import PER_HOUR, PER_MINUTE, ToolRateLimiter
from core.agent.tool_gate import run_tool_with_policy
from core.tools.policy import (
    effective_tool_risk,
    get_command_risk,
    get_tool_risk,
)
from core.tools.registry import ToolRegistry


class TestToolRisk:
    def test_read_allowed(self) -> None:
        assert get_tool_risk("read_file") == "allowed"

    def test_write_review(self) -> None:
        assert get_tool_risk("write_file") == "review"

    def test_git_push_blocked(self) -> None:
        assert get_command_risk("git push origin main") == "blocked"

    def test_effective_blocked_overrides(self) -> None:
        risk = effective_tool_risk(
            "execute_command", {"command": "git push origin main"}
        )
        assert risk == "blocked"


class TestToolGate:
    def _registry(self, result: dict | None = None) -> ToolRegistry:
        reg = ToolRegistry()
        reg.register(
            "read_file",
            "read",
            {"type": "object", "properties": {}, "required": []},
            lambda **_: result or {"success": True, "content": "ok"},
        )
        reg.register(
            "write_file",
            "write",
            {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["file_path", "content"],
            },
            lambda file_path, content: {
                "success": True,
                "path": file_path,
            },
        )
        return reg

    def test_allowed_no_confirm_handler(self) -> None:
        reg = self._registry()
        handler = MagicMock(return_value=False)
        result = run_tool_with_policy(
            reg,
            "read_file",
            {"file_path": "a.txt"},
            rate_key="test:1",
            confirm_handler=handler,
        )
        assert result["success"] is True
        handler.assert_not_called()

    def test_review_denied(self) -> None:
        reg = self._registry()
        result = run_tool_with_policy(
            reg,
            "write_file",
            {"file_path": "a.txt", "content": "x"},
            rate_key="test:2",
            confirm_handler=lambda _t, _a: False,
        )
        assert result["success"] is False
        assert result["policy"] == "user_denied"

    def test_review_allowed_executes(self) -> None:
        reg = self._registry()
        result = run_tool_with_policy(
            reg,
            "write_file",
            {"file_path": "a.txt", "content": "x"},
            rate_key="test:3",
            confirm_handler=lambda _t, _a: True,
        )
        assert result["success"] is True

    def test_blocked_no_handler_call(self) -> None:
        reg = self._registry()
        handler = MagicMock(return_value=True)
        result = run_tool_with_policy(
            reg,
            "execute_command",
            {"command": "git push origin main"},
            rate_key="test:4",
            confirm_handler=handler,
        )
        assert result["policy"] == "blocked"
        handler.assert_not_called()


class TestConfirmationManager:
    def test_resolve_wakes_wait(self) -> None:
        mgr = ConfirmationManager()
        events: list[dict] = []

        def worker() -> None:
            ok = mgr.request(
                session_id="s1",
                user_id="u1",
                tool="write_file",
                args={"file_path": "x.txt", "content": "hi"},
                on_event=lambda e: events.append(e),
            )
            assert ok is True

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.05)
        assert len(events) == 1
        assert events[0]["event"] == "confirmation_required"
        cid = events[0]["confirmation_id"]
        assert mgr.resolve(cid, user_id="u1", session_id="s1", allowed=True)
        t.join(timeout=2)
        assert not t.is_alive()


class TestRateLimiter:
    def test_rate_limit_triggers(self) -> None:
        limiter = ToolRateLimiter()
        key = "u:s"
        for _ in range(PER_MINUTE):
            assert limiter.check(key) is None
            limiter.record(key)
        err = limiter.check(key)
        assert err is not None
        assert err["policy"] == "rate_limit"

    def test_rate_limit_in_gate(self) -> None:
        reg = ToolRegistry()
        reg.register(
            "read_file",
            "r",
            {"type": "object", "properties": {}, "required": []},
            lambda **_: {"success": True},
        )
        limiter = ToolRateLimiter()
        key = "burst"
        for _ in range(PER_MINUTE):
            limiter.record(key)
        # patch get_rate_limiter for this test
        import core.agent.tool_gate as tg

        original = tg.get_rate_limiter
        tg.get_rate_limiter = lambda: limiter
        try:
            err = run_tool_with_policy(
                reg, "read_file", {}, rate_key=key, confirm_handler=None
            )
            assert err["policy"] == "rate_limit"
        finally:
            tg.get_rate_limiter = original
