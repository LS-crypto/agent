"""工具执行门禁：风险分级 + 确认 + 速率限制。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.agent.permissions import PermissionTier, get_permission_tier
from core.agent.rate_limit import get_rate_limiter
from core.tools.policy import (
    blocked_tool_message,
    effective_tool_risk,
    policy_error,
)
from core.tools.registry import ToolRegistry


def run_tool_with_policy(
    registry: ToolRegistry,
    tool_name: str,
    args: dict[str, Any],
    *,
    rate_key: str,
    confirm_handler: Callable[[str, dict[str, Any]], bool] | None = None,
    permission_tier: PermissionTier | None = None,
) -> dict[str, Any]:
    limiter = get_rate_limiter()
    rate_err = limiter.check(rate_key)
    if rate_err:
        return rate_err

    tier = permission_tier or get_permission_tier()
    risk = effective_tool_risk(tool_name, args, tier=tier)

    if risk == "blocked":
        return policy_error(blocked_tool_message(tool_name, args), "blocked")

    if risk == "review":
        if confirm_handler is None:
            return policy_error("需要用户确认但未提供确认处理器", "user_denied")
        if not confirm_handler(tool_name, args):
            return policy_error("用户拒绝执行", "user_denied")

    limiter.record(rate_key)
    return registry.execute(tool_name, args)
