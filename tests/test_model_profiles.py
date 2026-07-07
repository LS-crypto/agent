"""模型特色配置测试。"""

from __future__ import annotations

from core.models.catalog import AUTO_MODEL_ID
from core.models.profiles import get_model_profile, profile_to_api


def test_flash_profile_fast():
    p = get_model_profile("qwen3.6-flash")
    assert p.max_iterations <= 8
    assert "极速" in p.features[0] or "闪电" in p.tagline


def test_coder_profile_has_code_review_skill():
    p = get_model_profile("qwen3-coder-plus")
    assert "code-review" in p.skills


def test_long_profile_wide_read():
    p = get_model_profile("qwen-long")
    assert p.max_read_chars == 120_000
    assert p.enable_compression is False


def test_profile_to_api():
    data = profile_to_api("qwen3.7-plus")
    assert "features" in data
    assert "tagline" in data
    assert isinstance(data["features"], list)


def test_auto_profile():
    p = get_model_profile(AUTO_MODEL_ID)
    assert "路由" in p.tagline or "智能" in p.tagline
