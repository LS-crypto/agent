"""模型列表 API。"""



from __future__ import annotations



from fastapi import APIRouter, Depends, HTTPException, Query



from core.models.catalog import AUTO_MODEL_ID, get_catalog_entry

from core.models.profiles import profile_to_api

from core.models.sync import list_agent_models

from server.auth.dependencies import AuthUser, get_current_user

from server.services.model_policy import ModelNotAllowedError, filter_models_catalog, resolve_model_for_role



router = APIRouter(prefix="/models", tags=["models"])





@router.get("")

def get_models(

    check_remote: bool = Query(default=True, description="是否与百炼 API 校验可用性"),

    user: AuthUser = Depends(get_current_user),

) -> dict:

    catalog = list_agent_models(check_remote=check_remote)

    return filter_models_catalog(user.role, catalog)





@router.get("/{model_id}/profile")

def get_model_profile_api(

    model_id: str,

    user: AuthUser = Depends(get_current_user),

) -> dict:

    try:

        resolve_model_for_role(user.role, model_id)

    except ModelNotAllowedError as exc:

        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if model_id != AUTO_MODEL_ID and get_catalog_entry(model_id) is None:

        raise HTTPException(status_code=404, detail=f"未知模型: {model_id}")

    return {"model_id": model_id, **profile_to_api(model_id)}

