"""A 为辅：从百炼 API 拉取账号可用模型，与静态目录求交。"""

from __future__ import annotations

import logging
from typing import Any

from core.config import create_client
from core.models.catalog import (
    AUTO_MODEL_ID,
    AGENT_MODEL_CATALOG,
    get_default_model_id,
)
from core.models.profiles import get_model_profile, profile_to_api

logger = logging.getLogger(__name__)

# 远程 id 含这些片段且不在静态目录时，仍拒绝（非对话 Agent 用途）
_REMOTE_BLOCK_SUBSTR = (
    "embedding",
    "vision",
    "vl",
    "audio",
    "tts",
    "image",
    "ocr",
    "rerank",
    "gte-",
    "text-embedding",
)


def fetch_remote_model_ids() -> set[str] | None:
    """拉取账号下模型 id；失败返回 None（不阻断，静态目录仍可用）。"""
    try:
        client = create_client()
        page = client.models.list()
        ids: set[str] = set()
        for item in page.data:
            mid = getattr(item, "id", None)
            if mid:
                ids.add(mid)
        return ids
    except Exception as exc:
        logger.warning("拉取远程模型列表失败，仅使用静态目录: %s", exc)
        return None


def _remote_blocked(model_id: str) -> bool:
    lower = model_id.lower()
    return any(s in lower for s in _REMOTE_BLOCK_SUBSTR)


def list_agent_models(*, check_remote: bool = True) -> dict[str, Any]:
    """返回 Web/CLI 可用的模型列表（仅 Agent 择优目录 + 可用性标记）。"""
    remote = fetch_remote_model_ids() if check_remote else None
    default_id = get_default_model_id()

    models: list[dict[str, Any]] = [
        {
            "id": AUTO_MODEL_ID,
            "label": "自动路由",
            "group": "推荐",
            "tier": "auto",
            "description": "按任务复杂度自动选择 Flash / Plus / Max",
            "supports_tools": True,
            "available": True,
            "is_default": False,
            **profile_to_api(AUTO_MODEL_ID),
        }
    ]

    for entry in AGENT_MODEL_CATALOG:
        if not entry.supports_tools:
            continue
        if remote is None:
            available = True
        else:
            available = entry.id in remote
        models.append(
            {
                "id": entry.id,
                "label": entry.label,
                "group": entry.group,
                "tier": entry.tier,
                "description": entry.description,
                "max_tokens": entry.max_tokens,
                "supports_tools": entry.supports_tools,
                "available": available,
                "is_default": entry.id == default_id,
                **profile_to_api(entry.id),
            }
        )

    # 远程有、静态未收录的 qwen 对话模型：仅记录日志，不自动加入（保持择优）
    if remote:
        extra = [
            mid
            for mid in sorted(remote)
            if mid.startswith("qwen")
            and mid not in {m.id for m in AGENT_MODEL_CATALOG}
            and not _remote_blocked(mid)
        ]
        if extra:
            logger.debug("远程额外 qwen 模型（未纳入目录）: %s", extra[:10])

    return {
        "default_model": default_id,
        "auto_model_id": AUTO_MODEL_ID,
        "models": models,
        "remote_checked": remote is not None,
    }


def list_available_model_ids(*, check_remote: bool = True) -> list[str]:
    """仅返回当前可用的 Agent 模型 id（不含 auto）。"""
    data = list_agent_models(check_remote=check_remote)
    return [
        m["id"]
        for m in data["models"]
        if m["id"] != AUTO_MODEL_ID and m.get("available", True)
    ]
