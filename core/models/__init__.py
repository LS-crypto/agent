"""模型目录：静态择优 + 远程可用性校验。"""

from core.models.catalog import (
    AUTO_MODEL_ID,
    AGENT_MODEL_CATALOG,
    get_catalog_entry,
    get_default_model_id,
    is_agent_model,
    resolve_model_choice,
)
from core.models.sync import fetch_remote_model_ids, list_agent_models, list_available_model_ids

__all__ = [
    "AUTO_MODEL_ID",
    "AGENT_MODEL_CATALOG",
    "get_catalog_entry",
    "get_default_model_id",
    "is_agent_model",
    "resolve_model_choice",
    "fetch_remote_model_ids",
    "list_agent_models",
    "list_available_model_ids",
]
