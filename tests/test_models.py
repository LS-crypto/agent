"""模型目录与 /api/models 测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.models.catalog import (
    AUTO_MODEL_ID,
    get_default_model_id,
    is_agent_model,
    resolve_model_choice,
)
from core.models.sync import list_agent_models
from server.main import app


def test_resolve_model_choice_auto():
    fixed, route = resolve_model_choice("auto")
    assert fixed is None
    assert route is True


def test_resolve_model_choice_none():
    fixed, route = resolve_model_choice(None)
    assert fixed is None
    assert route is True


def test_resolve_model_choice_fixed():
    fixed, route = resolve_model_choice("qwen3.7-plus")
    assert fixed == "qwen3.7-plus"
    assert route is False


def test_resolve_model_choice_invalid():
    with pytest.raises(ValueError, match="不可用作 Agent"):
        resolve_model_choice("text-embedding-v3")


def test_is_agent_model():
    assert is_agent_model("qwen3.7-plus") is True
    assert is_agent_model("unknown-model") is False


def test_list_agent_models_structure():
    data = list_agent_models(check_remote=False)
    assert data["auto_model_id"] == AUTO_MODEL_ID
    assert data["default_model"] == get_default_model_id()
    ids = [m["id"] for m in data["models"]]
    assert AUTO_MODEL_ID in ids
    assert "qwen3.7-plus" in ids
    auto = next(m for m in data["models"] if m["id"] == AUTO_MODEL_ID)
    assert auto["label"] == "自动路由"


def test_api_get_models():
    with TestClient(app) as client:
        res = client.get("/api/models?check_remote=false")
    assert res.status_code == 200
    body = res.json()
    assert "models" in body
    assert len(body["models"]) >= 2


def test_session_model_validation():
    with TestClient(app) as client:
        created = client.post(
            "/api/sessions",
            json={"user_id": "default", "title": "模型测试", "model": "auto"},
        ).json()
        session_id = created["id"]

        bad = client.patch(
            f"/api/sessions/{session_id}/model",
            params={"user_id": "default"},
            json={"model": "text-embedding-v3"},
        )
        assert bad.status_code == 400

        ok = client.patch(
            f"/api/sessions/{session_id}/model",
            params={"user_id": "default"},
            json={"model": "qwen-max"},
        )
        assert ok.status_code == 200
        assert ok.json()["model"] == "qwen-max"

        client.delete(f"/api/sessions/{session_id}", params={"user_id": "default"})
