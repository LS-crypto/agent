"""多模态聊天图片测试。"""

from __future__ import annotations

import base64

import pytest

from core.agent.multimodal import (
    ChatImageError,
    build_user_content,
    extract_images,
    extract_text,
    resolve_vision_model,
    validate_data_url,
    validate_image_list,
)


def _png_data_url() -> str:
    # 1x1 PNG
    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def test_validate_data_url_ok() -> None:
    url = validate_data_url(_png_data_url())
    assert url.startswith("data:image/png;base64,")


def test_validate_data_url_rejects_invalid() -> None:
    with pytest.raises(ChatImageError):
        validate_data_url("https://example.com/a.png")


def test_build_user_content_text_only() -> None:
    assert build_user_content("hello", None) == "hello"


def test_build_user_content_with_images() -> None:
    content = build_user_content("看这张图", [_png_data_url()])
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"


def test_build_user_content_images_only_default_prompt() -> None:
    content = build_user_content("", [_png_data_url()])
    assert isinstance(content, list)
    assert content[0]["text"] == "请描述这张图片。"


def test_extract_text_and_images() -> None:
    content = build_user_content("说明", [_png_data_url()])
    assert "说明" in extract_text(content)
    assert len(extract_images(content)) == 1


def test_resolve_vision_model_auto() -> None:
    assert resolve_vision_model("auto") == "qwen3-vl-flash"


def test_resolve_vision_model_fallback_for_non_vision() -> None:
    """非视觉模型带图时自动降级到默认 VL 模型，不再报错。"""
    assert resolve_vision_model("qwen3.7-plus") == "qwen3-vl-flash"
    assert resolve_vision_model("qwen3.6-flash") == "qwen3-vl-flash"


def test_validate_image_list_limit() -> None:
    urls = [_png_data_url() for _ in range(5)]
    with pytest.raises(ChatImageError):
        validate_image_list(urls)
