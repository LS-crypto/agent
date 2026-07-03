"""模型列表 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from core.models.catalog import AUTO_MODEL_ID, get_catalog_entry
from core.models.profiles import profile_to_api
from core.models.sync import list_agent_models

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def get_models(
    check_remote: bool = Query(default=True, description="是否与百炼 API 校验可用性"),
) -> dict:
    return list_agent_models(check_remote=check_remote)


@router.get("/{model_id}/profile")
def get_model_profile_api(model_id: str) -> dict:
    if model_id != AUTO_MODEL_ID and get_catalog_entry(model_id) is None:
        raise HTTPException(status_code=404, detail=f"未知模型: {model_id}")
    return {"model_id": model_id, **profile_to_api(model_id)}
