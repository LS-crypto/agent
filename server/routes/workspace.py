"""用户工作区 API：沙箱文件树与预览。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from server.auth.dependencies import AuthUser, get_current_user
from server.schemas import (
    WorkspaceFileContentResponse,
    WorkspaceFilesResponse,
    WorkspaceInfoResponse,
)
from server.services.user_provision import provision_user_storage
from server.services.workspace_reader import (
    get_workspace_info,
    list_workspace_files,
    read_workspace_file,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _ensure_workspace(user: AuthUser) -> None:
    provision_user_storage(user.id, email=user.email)


@router.get("", response_model=WorkspaceInfoResponse)
def workspace_info(user: AuthUser = Depends(get_current_user)) -> WorkspaceInfoResponse:
    _ensure_workspace(user)
    info = get_workspace_info(user.id)
    return WorkspaceInfoResponse(**info)


@router.get("/files", response_model=WorkspaceFilesResponse)
def workspace_files(
    path: str = Query(default=".", description="相对子目录，默认项目根"),
    user: AuthUser = Depends(get_current_user),
) -> WorkspaceFilesResponse:
    _ensure_workspace(user)
    result = list_workspace_files(user.id, subpath=path)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "无法列出目录"),
        )
    return WorkspaceFilesResponse(
        path=result["path"],
        entries=result["entries"],
        count=result["count"],
        truncated=bool(result.get("truncated")),
    )


@router.get("/file", response_model=WorkspaceFileContentResponse)
def workspace_file(
    path: str = Query(min_length=1, description="文件相对路径"),
    user: AuthUser = Depends(get_current_user),
) -> WorkspaceFileContentResponse:
    _ensure_workspace(user)
    result = read_workspace_file(user.id, path)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "无法读取文件"),
        )
    return WorkspaceFileContentResponse(
        path=result["path"],
        content=result["content"],
        truncated=bool(result.get("truncated")),
    )
