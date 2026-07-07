"""API 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class AuthUserResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str
    created_at: str | None = None
    last_login_at: str | None = None
    display_name: str | None = None
    avatar: str | None = None


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=32)
    avatar: str | None = Field(default=None, min_length=1, max_length=8)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    model: str | None = Field(
        default=None,
        description="模型 id 或 auto；None 表示使用会话已存选择",
    )
    enable_routing: bool | None = Field(
        default=None,
        description="None=随 model 自动；True/False 强制覆盖",
    )
    enable_compression: bool = Field(default=True, description="启用工具结果压缩")
    permission: str | None = Field(
        default=None,
        description="权限档位 conservative/balanced/permissive；None 用会话已存",
    )


class SessionCreateRequest(BaseModel):
    title: str = Field(default="新会话", min_length=1)
    model: str | None = Field(
        default=None,
        description="模型 id；省略时按角色使用默认模型（普通用户不可传 auto）",
    )
    permission: str = Field(
        default="balanced",
        description="conservative | balanced | permissive",
    )


class SessionModelRequest(BaseModel):
    model: str = Field(min_length=1)


class SessionPermissionRequest(BaseModel):
    permission: str = Field(min_length=1)


class SessionRenameRequest(BaseModel):
    title: str = Field(min_length=1)


class ChatConfirmRequest(BaseModel):
    session_id: str = Field(min_length=1)
    confirmation_id: str = Field(min_length=1)
    allowed: bool


class ApiKeySaveRequest(BaseModel):
    api_key: str = Field(min_length=8, max_length=256)


class ApiKeyStatusResponse(BaseModel):
    configured: bool
    hint: str | None = None
    uses_platform_key: bool = False
    updated_at: str | None = None


class AdminBanRequest(BaseModel):
    status: str = Field(description="active 或 banned")


class AdminUserSummary(BaseModel):
    id: str
    email: str
    role: str
    status: str
    created_at: str | None = None
    last_login_at: str | None = None
    has_api_key: bool = False
    session_count: int = 0
    workspace_dir: str | None = None
    projects_dir: str | None = None
    db_path: str | None = None


class WorkspaceEntry(BaseModel):
    path: str
    name: str
    type: str
    size: int | None = None


class WorkspaceInfoResponse(BaseModel):
    root: str
    projects_dir: str
    file_count: int
    total_bytes: int
    total_size: str
    largest_file: str | None = None
    mode: str = "sandbox"
    sandbox_path: str | None = None
    local_path: str | None = None
    local_folder_enabled: bool = False
    quota_bytes: int | None = None
    quota_size: str | None = None
    quota_remaining_bytes: int | None = None
    quota_remaining_size: str | None = None
    quota_percent_used: float | None = None


class WorkspaceOpenFolderRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class WorkspaceBindingResponse(BaseModel):
    mode: str
    root: str
    sandbox_path: str
    local_path: str | None = None
    local_folder_enabled: bool


class WorkspaceFilesResponse(BaseModel):
    path: str
    entries: list[WorkspaceEntry]
    count: int
    truncated: bool = False


class WorkspaceFileContentResponse(BaseModel):
    path: str
    content: str
    truncated: bool = False
