"""权限档位与确认说明测试。"""

from __future__ import annotations

import pytest

from core.agent.permissions import normalize_tier, set_permission_tier
from core.tools.policy import (
    build_confirmation_detail,
    effective_tool_risk,
    get_tool_risk,
)


def test_normalize_tier_invalid():
    with pytest.raises(ValueError, match="无效权限"):
        normalize_tier("ultra")


def test_conservative_use_skill_review():
    set_permission_tier("conservative")
    assert get_tool_risk("use_skill", tier="conservative") == "review"


def test_permissive_use_skill_allowed():
    assert get_tool_risk("use_skill", tier="permissive") == "allowed"


def test_blocked_always_blocked():
    set_permission_tier("permissive")
    risk = effective_tool_risk(
        "execute_command",
        {"command": "rm -rf ."},
        tier="permissive",
    )
    assert risk == "blocked"


def test_confirmation_detail_execute_command():
    detail = build_confirmation_detail(
        "execute_command",
        {"command": "pytest tests/"},
        tier="balanced",
    )
    assert detail["severity"] in ("medium", "high")
    assert "pytest" in detail["summary"] or "pytest" in detail["explanation"]
    assert detail["impact"]
