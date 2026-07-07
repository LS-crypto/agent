"""J1 BYOK 测试。"""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user, save_user_api_key


def test_user_without_key_cannot_chat(client: TestClient) -> None:
    auth = register_user(client, email="no-key@example.com")
    headers = auth_headers(auth["access_token"])

    created = client.post(
        "/api/sessions",
        json={"title": "需要 Key"},
        headers=headers,
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    res = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "你好"},
        headers=headers,
    )
    assert res.status_code == 403
    assert "DashScope" in res.json()["detail"]


def test_save_and_status_api_key(client: TestClient) -> None:
    auth = register_user(client, email="byok@example.com")
    headers = auth_headers(auth["access_token"])

    before = client.get("/api/settings/api-key", headers=headers)
    assert before.status_code == 200
    assert before.json()["configured"] is False

    save_user_api_key(client, auth["access_token"], "sk-mysecretkey1234567890")

    after = client.get("/api/settings/api-key", headers=headers)
    assert after.status_code == 200
    body = after.json()
    assert body["configured"] is True
    assert body["hint"] == "sk-***7890"
    assert "sk-mysecretkey1234567890" not in str(body)


def test_api_key_stored_encrypted_not_plaintext(
    client: TestClient,
    db_path,
) -> None:
    auth = register_user(client, email="encrypt@example.com")
    save_user_api_key(client, auth["access_token"], "sk-plaintextmustnotappear")

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT ciphertext FROM user_secrets").fetchall()
    conn.close()

    assert len(rows) == 1
    blob = rows[0][0]
    assert "sk-plaintextmustnotappear" not in blob
    assert len(blob) > 20


def test_delete_api_key(client: TestClient) -> None:
    auth = register_user(client, email="del-key@example.com")
    headers = auth_headers(auth["access_token"])
    save_user_api_key(client, auth["access_token"])

    deleted = client.delete("/api/settings/api-key", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["configured"] is False
