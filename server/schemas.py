"""API 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(default="default", min_length=1)
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
    user_id: str = Field(default="default", min_length=1)
    title: str = Field(default="新会话", min_length=1)
    model: str = Field(default="auto", description="auto 或 catalog 中的 model id")
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
    user_id: str = Field(default="default", min_length=1)
    session_id: str = Field(min_length=1)
    confirmation_id: str = Field(min_length=1)
    allowed: bool
