"""Skills / 权限 / MCP 目录 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from core.agent.permissions import list_permission_tiers
from core.mcp.catalog import list_mcp_catalog
from core.mcp.status import list_mcp_status
from core.skills.loader import discover_skills
from server.auth.dependencies import AuthUser, get_current_user
from server.repositories.sessions import SessionRepository
from server.schemas import SessionPermissionRequest

router = APIRouter(tags=["meta"])
_repo = SessionRepository()


@router.get("/skills")
def get_skills() -> dict:
    skills = discover_skills()
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "path": str(s.path),
            }
            for s in skills
        ],
        "count": len(skills),
        "hint": "Agent 可调用 list_skills / use_skill 工具；用户亦可在对话中要求加载某技能",
    }


@router.get("/permissions")
def get_permissions() -> dict:
    return {"tiers": list_permission_tiers()}


@router.get("/mcp/catalog")
def get_mcp_catalog() -> dict:
    return list_mcp_catalog()


@router.get("/mcp/status")
def get_mcp_status(
    ping: bool = Query(default=False, description="是否探测 GitHub/Brave/内置 MCP 连通性"),
) -> dict:
    return list_mcp_status(ping=ping)


@router.patch("/sessions/{session_id}/permission")
def set_session_permission(
    session_id: str,
    body: SessionPermissionRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    try:
        return _repo.set_permission(session_id, user.id, body.permission)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
