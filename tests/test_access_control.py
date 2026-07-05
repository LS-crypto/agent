"""J3 注册上限与并发限制测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user


def test_registration_cap(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("MAX_REGISTERED_USERS", "2")
    register_user(client, email="cap1@example.com")
    register_user(client, email="cap2@example.com")
    res = client.post(
        "/api/auth/register",
        json={"email": "cap3@example.com", "password": "testpass123"},
    )
    assert res.status_code == 403
    assert "上限" in res.json()["detail"]
