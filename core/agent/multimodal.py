"""多模态用户消息：文本 + 图片（OpenAI 兼容格式）。"""

from __future__ import annotations

import base64
import os
import re
from typing import Any

from core.models.catalog import get_catalog_entry

_DATA_URL_RE = re.compile(
    r"^data:(image/(?:jpeg|png|gif|webp));base64,([A-Za-z0-9+/=\s]+)$",
    re.IGNORECASE,
)

DEFAULT_VISION_MODEL = os.getenv("DEFAULT_VISION_MODEL", "qwen3-vl-flash")
MAX_CHAT_IMAGES = int(os.getenv("CHAT_MAX_IMAGES", "4"))
MAX_CHAT_IMAGE_BYTES = int(os.getenv("CHAT_MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))


class ChatImageError(ValueError):
    """图片校验失败。"""


def validate_data_url(url: str) -> str:
    """校验 data URL，返回规范化后的 data URL。"""
    text = url.strip()
    match = _DATA_URL_RE.match(text)
    if not match:
        raise ChatImageError("图片须为 data:image/jpeg|png|gif|webp;base64,... 格式")
    mime = match.group(1).lower()
    payload = re.sub(r"\s+", "", match.group(2))
    try:
        raw = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise ChatImageError("图片 Base64 无效") from exc
    if not raw:
        raise ChatImageError("图片内容为空")
    if len(raw) > MAX_CHAT_IMAGE_BYTES:
        mb = MAX_CHAT_IMAGE_BYTES // (1024 * 1024)
        raise ChatImageError(f"单张图片不能超过 {mb}MB")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def validate_image_list(images: list[str] | None) -> list[str]:
    if not images:
        return []
    if len(images) > MAX_CHAT_IMAGES:
        raise ChatImageError(f"每条消息最多 {MAX_CHAT_IMAGES} 张图片")
    return [validate_data_url(item) for item in images]


def build_user_content(text: str, images: list[str] | None = None) -> str | list[dict[str, Any]]:
    """构建 user message content（纯文本或多模态数组）。"""
    normalized = validate_image_list(images)
    if not normalized:
        return text
    parts: list[dict[str, Any]] = []
    stripped = text.strip()
    parts.append({"type": "text", "text": stripped or "请描述这张图片。"})
    for url in normalized:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def extract_plain_text(content: Any) -> str:
    """提取用户可编辑的纯文本（不含图片数量后缀）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                chunks.append(part["text"])
        return "\n".join(chunks).strip()
    return str(content or "")


def extract_text(content: Any) -> str:
    """从 message content 提取可读文本（日志/标题用）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        image_count = 0
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                chunks.append(part["text"])
            elif part.get("type") == "image_url":
                image_count += 1
        text = "\n".join(chunks).strip()
        if image_count:
            suffix = f" [{image_count} 张图片]"
            return (text + suffix) if text else f"[{image_count} 张图片]"
        return text
    return str(content or "")


def extract_images(content: Any) -> list[str]:
    if isinstance(content, list):
        urls: list[str] = []
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "image_url":
                continue
            payload = part.get("image_url")
            if isinstance(payload, dict) and isinstance(payload.get("url"), str):
                urls.append(payload["url"])
        return urls
    return []


def model_supports_vision(model_id: str) -> bool:
    entry = get_catalog_entry(model_id)
    return bool(entry and entry.supports_vision)


def resolve_vision_model(model_id: str) -> str:
    """带图片时解析可用视觉模型：不支持视觉的模型自动降级到 DEFAULT_VISION_MODEL。"""
    if model_supports_vision(model_id):
        return model_id
    if not model_supports_vision(DEFAULT_VISION_MODEL):
        raise ChatImageError(f"默认视觉模型不可用: {DEFAULT_VISION_MODEL}")
    return DEFAULT_VISION_MODEL
