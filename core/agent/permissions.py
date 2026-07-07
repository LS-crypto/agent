"""Agent 权限档位：保守 / 平衡 / 宽松（均在安全基线内）。"""

from __future__ import annotations

import os
from contextvars import ContextVar
from typing import Any, Literal

PermissionTier = Literal["conservative", "balanced", "permissive"]

TIER_LABELS: dict[PermissionTier, str] = {
    "conservative": "保守",
    "balanced": "平衡",
    "permissive": "宽松",
}

TIER_DESCRIPTIONS: dict[PermissionTier, str] = {
    "conservative": "只读与系统信息自动执行；任何写入、命令、技能加载均需确认。",
    "balanced": "默认策略：读操作自动；写文件、执行命令、Git 提交需确认。",
    "permissive": "读与系统信息、技能查询自动；写入与命令仍需确认，Shell 白名单略宽。",
}

_current_tier: ContextVar[PermissionTier] = ContextVar(
    "permission_tier", default="balanced"
)


def get_default_tier() -> PermissionTier:
    raw = os.getenv("DEFAULT_PERMISSION_TIER", "balanced").strip().lower()
    if raw in TIER_LABELS:
        return raw  # type: ignore[return-value]
    return "balanced"


def normalize_tier(tier: str | None) -> PermissionTier:
    if not tier:
        return get_default_tier()
    t = tier.strip().lower()
    if t in TIER_LABELS:
        return t  # type: ignore[return-value]
    raise ValueError(f"无效权限档位: {tier}，可选: conservative, balanced, permissive")


def set_permission_tier(tier: PermissionTier) -> None:
    _current_tier.set(tier)


def get_permission_tier() -> PermissionTier:
    return _current_tier.get()


def list_permission_tiers() -> list[dict[str, Any]]:
    default = get_default_tier()
    return [
        {
            "id": tid,
            "label": TIER_LABELS[tid],
            "description": TIER_DESCRIPTIONS[tid],
            "is_default": tid == default,
        }
        for tid in ("conservative", "balanced", "permissive")
    ]
