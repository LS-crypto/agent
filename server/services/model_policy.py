"""J2：按角色限制可用模型。"""

from __future__ import annotations

import os
from typing import Any

from core.models.catalog import AUTO_MODEL_ID, get_catalog_entry

_DEFAULT_USER_MODELS = ("qwen3.6-flash",)


class ModelNotAllowedError(ValueError):
    """用户请求了无权使用的模型。"""


def user_allowed_model_ids() -> frozenset[str]:
    raw = os.getenv("USER_ALLOWED_MODELS", "").strip()
    if not raw:
        return frozenset(_DEFAULT_USER_MODELS)
    ids = {part.strip() for part in raw.split(",") if part.strip()}
    return frozenset(ids) if ids else frozenset(_DEFAULT_USER_MODELS)


def default_model_for_role(role: str) -> str:
    if role == "admin":
        return AUTO_MODEL_ID
    allowed = user_allowed_model_ids()
    raw = os.getenv("USER_ALLOWED_MODELS", "").strip()
    if raw:
        for part in raw.split(","):
            mid = part.strip()
            if mid in allowed:
                return mid
    return next(iter(allowed))


def resolve_model_for_role(role: str, requested: str | None) -> str:
    """解析并校验模型 id；无权时抛 ModelNotAllowedError。"""
    if role == "admin":
        model = requested or AUTO_MODEL_ID
        if model != AUTO_MODEL_ID and get_catalog_entry(model) is None:
            raise ModelNotAllowedError(f"未知模型: {model}")
        return model

    model = requested or default_model_for_role(role)
    allowed = user_allowed_model_ids()
    if model == AUTO_MODEL_ID:
        raise ModelNotAllowedError("普通用户不可使用自动路由")
    if model not in allowed:
        raise ModelNotAllowedError(f"无权使用该模型: {model}")
    if get_catalog_entry(model) is None:
        raise ModelNotAllowedError(f"未知模型: {model}")
    return model


def filter_models_catalog(role: str, catalog: dict[str, Any]) -> dict[str, Any]:
    if role == "admin":
        return catalog

    allowed = user_allowed_model_ids()
    models = [m for m in catalog["models"] if m.get("id") in allowed]
    default = default_model_for_role(role)
    return {
        **catalog,
        "default_model": default,
        "models": models,
        "role_restricted": True,
    }
