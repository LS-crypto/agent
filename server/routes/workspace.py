"""用户工作区 API：沙箱文件树与预览。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from core.user.workspace_binding import (
    get_binding_info,
    reset_to_sandbox,
    set_local_folder,
)
from server.auth.dependencies import AuthUser, get_current_user
from server.schemas import (
    WorkspaceBindingResponse,
    WorkspaceFileContentResponse,
    WorkspaceFilesResponse,
    WorkspaceInfoResponse,
    WorkspaceOpenFolderRequest,
    WorkspaceUploadResponse,
)
from server.services.workspace_upload import (
    WorkspaceQuotaError,
    WorkspaceUploadError,
    upload_response_payload,
    upload_workspace_zip,
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


@router.get("/binding", response_model=WorkspaceBindingResponse)
def workspace_binding(user: AuthUser = Depends(get_current_user)) -> WorkspaceBindingResponse:
    _ensure_workspace(user)
    return WorkspaceBindingResponse(**get_binding_info(user.id))


@router.post("/open-folder", response_model=WorkspaceBindingResponse)
def workspace_open_folder(
    body: WorkspaceOpenFolderRequest,
    user: AuthUser = Depends(get_current_user),
) -> WorkspaceBindingResponse:
    _ensure_workspace(user)
    try:
        info = set_local_folder(user.id, body.path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return WorkspaceBindingResponse(**info)


@router.post("/reset-folder", response_model=WorkspaceBindingResponse)
def workspace_reset_folder(
    user: AuthUser = Depends(get_current_user),
) -> WorkspaceBindingResponse:
    _ensure_workspace(user)
    return WorkspaceBindingResponse(**reset_to_sandbox(user.id))


def _parse_strip_root(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in ("1", "true", "yes", "on")


@router.post("/upload", response_model=WorkspaceUploadResponse)
async def workspace_upload(
    file: UploadFile = File(...),
    mode: str = Form(default="merge"),
    target_dir: str | None = Form(default=None),
    strip_root: str | None = Form(default="true"),
    user: AuthUser = Depends(get_current_user),
) -> WorkspaceUploadResponse:
    """上传 zip 到云端沙箱 projects/（ECS 替代「打开本机文件夹」）。"""
    _ensure_workspace(user)

    filename = (file.filename or "").lower()
    if not filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传 .zip 文件",
        )

    raw = await file.read()
    try:
        result = upload_workspace_zip(
            user.id,
            raw,
            mode=mode.strip().lower(),
            target_dir=target_dir,
            strip_root=_parse_strip_root(strip_root),
        )
    except WorkspaceQuotaError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except WorkspaceUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return WorkspaceUploadResponse(**upload_response_payload(user.id, result))
