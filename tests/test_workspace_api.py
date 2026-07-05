"""工作区 API 测试。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from core.user.paths import workspace_projects
from tests.conftest import auth_headers, register_user


def test_workspace_info_and_files(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="ws@example.com")
    user_id = auth["user"]["id"]
    token = auth["access_token"]
    headers = auth_headers(token)

    projects = workspace_projects(user_id)
    projects.mkdir(parents=True, exist_ok=True)
    (projects / "hello.py").write_text("print('hi')\n", encoding="utf-8")
    sub = projects / "src"
    sub.mkdir()
    (sub / "main.py").write_text("x = 1\n", encoding="utf-8")

    info = client.get("/api/workspace", headers=headers)
    assert info.status_code == 200
    body = info.json()
    assert body["file_count"] == 2
    assert Path(body["projects_dir"]) == projects.resolve()

    listing = client.get("/api/workspace/files", headers=headers)
    assert listing.status_code == 200
    entries = listing.json()["entries"]
    paths = {e["path"] for e in entries}
    assert "hello.py" in paths
    assert "src/main.py" in paths or "src" in paths

    content = client.get("/api/workspace/file", params={"path": "hello.py"}, headers=headers)
    assert content.status_code == 200
    assert "print('hi')" in content.json()["content"]


def test_workspace_requires_auth(client: TestClient) -> None:
    res = client.get("/api/workspace")
    assert res.status_code == 401


def test_workspace_file_not_found(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="ws-miss@example.com")
    headers = auth_headers(auth["access_token"])

    res = client.get(
        "/api/workspace/file",
        params={"path": "missing.txt"},
        headers=headers,
    )
    assert res.status_code == 400
