"""多模态聊天图片测试（DeepSeek 不支持视觉，功能已禁用）。"""

from __future__ import annotations

import base64

import pytest

from core.agent.multimodal import (
    ChatImageError,
    build_user_content,
    extract_images,
    extract_text,
    resolve_vision_model,
    strip_unsupported_images,
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


def test_build_user_content_with_images_rejected() -> None:
    """DeepSeek 不支持图片，发送图片应报错。"""
    with pytest.raises(ChatImageError, match="不支持图片"):
        build_user_content("看这张图", [_png_data_url()])


def test_resolve_vision_model_rejected() -> None:
    """DeepSeek 没有视觉模型，应抛出错误。"""
    with pytest.raises(ChatImageError, match="不支持图片"):
        resolve_vision_model("deepseek-chat")


def test_validate_image_list_rejected() -> None:
    """图片功能已禁用。"""
    urls = [_png_data_url()]
    with pytest.raises(ChatImageError, match="不支持图片"):
        validate_image_list(urls)


def test_extract_text_and_images_empty() -> None:
    """纯文本内容正常处理。"""
    content = build_user_content("说明", None)
    assert "说明" in extract_text(content)
    assert len(extract_images(content)) == 0


def test_strip_unsupported_images_noop_when_supports_vision() -> None:
    """支持视觉的模型不清洗，原样返回。"""
    msgs = [
        {"role": "user", "content": [
            {"type": "text", "text": "看图"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}},
        ]}
    ]
    assert strip_unsupported_images(msgs, supports_vision=True) is msgs


def test_strip_unsupported_images_replaces_image_url() -> None:
    """不支持视觉时，把 image_url 替换为占位文本，避免污染 API 请求。"""
    msgs = [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": [
            {"type": "text", "text": "看这张图"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}},
        ]},
    ]
    cleaned = strip_unsupported_images(msgs, supports_vision=False)

    # system 消息原样保留
    assert cleaned[0] == msgs[0]
    # user 消息：image_url 被替换为文本占位，原文本保留
    user_content = cleaned[1]["content"]
    assert isinstance(user_content, list)
    assert all(p["type"] == "text" for p in user_content)
    assert "看这张图" in user_content[0]["text"]
    assert "1 张图片已隐藏" in user_content[-1]["text"]


def test_strip_unsupported_images_counts_multiple_images() -> None:
    """多条图片计数正确。"""
    msgs = [
        {"role": "user", "content": [
            {"type": "text", "text": ""},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,a"}},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,b"}},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,c"}},
        ]}
    ]
    cleaned = strip_unsupported_images(msgs, supports_vision=False)
    note = cleaned[0]["content"][-1]["text"]
    assert "3 张图片已隐藏" in note


def test_strip_unsupported_images_clean_messages_unchanged() -> None:
    """干净的 messages 不被改动。"""
    msgs = [
        {"role": "system", "content": "hi"},
        {"role": "user", "content": "普通问题"},
        {"role": "assistant", "content": "回答"},
    ]
    cleaned = strip_unsupported_images(msgs, supports_vision=False)
    assert cleaned == msgs


def test_strip_unsupported_images_does_not_mutate_input() -> None:
    """深拷贝语义：不修改入参 messages。"""
    original = [
        {"role": "user", "content": [
            {"type": "text", "text": "看图"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}},
        ]}
    ]
    import copy
    snapshot = copy.deepcopy(original)
    strip_unsupported_images(original, supports_vision=False)
    assert original == snapshot


def test_strip_unsupported_images_skips_only_image_message() -> None:
    """消息里只有图片没有文本时也能正常处理（生成纯占位）。"""
    msgs = [
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}},
        ]}
    ]
    cleaned = strip_unsupported_images(msgs, supports_vision=False)
    parts = cleaned[0]["content"]
    assert len(parts) == 1
    assert "1 张图片已隐藏" in parts[0]["text"]
