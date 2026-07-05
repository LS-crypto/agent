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
from tests.conftest import auth_headers, register_user


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


def test_api_get_models(client: TestClient):
    auth = register_user(client)
    headers = auth_headers(auth["access_token"])
    res = client.get("/api/models?check_remote=false", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert "models" in body
    assert len(body["models"]) >= 1
    assert body.get("role_restricted") is True
    ids = {m["id"] for m in body["models"]}
    assert "auto" not in ids


def test_session_model_validation(client: TestClient):
    auth = register_user(client)
    headers = auth_headers(auth["access_token"])
    created = client.post(
        "/api/sessions",
        json={"title": "模型测试", "model": "qwen3.6-flash"},
        headers=headers,
    ).json()
    session_id = created["id"]

    bad = client.patch(
        f"/api/sessions/{session_id}/model",
        json={"model": "text-embedding-v3"},
        headers=headers,
    )
    assert bad.status_code == 403

    denied = client.patch(
        f"/api/sessions/{session_id}/model",
        json={"model": "qwen-max"},
        headers=headers,
    )
    assert denied.status_code == 403

    ok = client.patch(
        f"/api/sessions/{session_id}/model",
        json={"model": "qwen3.6-flash"},
        headers=headers,
    )
    assert ok.status_code == 200
    assert ok.json()["model"] == "qwen3.6-flash"

    client.delete(f"/api/sessions/{session_id}", headers=headers)
