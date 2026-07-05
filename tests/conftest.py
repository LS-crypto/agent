"""测试公共 fixture。"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.db.database import init_db
from server.main import app


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "sessions.sqlite"


@pytest.fixture
def client(
    db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("server.db.database.runtime_db_path", lambda: db_path)
    monkeypatch.setenv("MASTER_SECRET", "test-master-secret-for-byok")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-platform-key-for-admin")
    init_db()
    with TestClient(app) as c:
        yield c


def register_user(
    client: TestClient,
    *,
    email: str | None = None,
    password: str = "testpass123",
) -> dict:
    if email is None:
        email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
    )
    assert res.status_code == 201, res.text
    return res.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def save_user_api_key(
    client: TestClient,
    token: str,
    api_key: str = "sk-testuserkey1234567890",
) -> None:
    res = client.put(
        "/api/settings/api-key",
        json={"api_key": api_key},
        headers=auth_headers(token),
    )
    assert res.status_code == 200, res.text


@pytest.fixture
def auth_client(client: TestClient) -> tuple[TestClient, dict[str, str], dict]:
    payload = register_user(client)
    headers = auth_headers(payload["access_token"])
    return client, headers, payload["user"]
