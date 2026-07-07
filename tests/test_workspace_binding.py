"""本机文件夹绑定（阶段 N3）测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.tools.filesystem import FileSystemTools
from core.user.workspace_binding import (
    get_binding_info,
    reset_to_sandbox,
    resolve_workspace_root,
    set_local_folder,
    validate_local_folder,
)
from tests.conftest import auth_headers, register_user


@pytest.fixture
def runtime_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)
    return runtime


def test_resolve_sandbox_by_default(runtime_root: Path) -> None:
    root = resolve_workspace_root("user-a")
    assert root == (runtime_root / "workspaces" / "user-a" / "projects").resolve()
    info = get_binding_info("user-a")
    assert info["mode"] == "sandbox"


def test_open_local_folder(runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_LOCAL_FOLDER", "1")
    local = runtime_root / "external-project"
    local.mkdir(parents=True)
    (local / "main.py").write_text("print(1)\n", encoding="utf-8")

    info = set_local_folder("user-b", str(local))
    assert info["mode"] == "local"
    assert Path(info["root"]) == local.resolve()

    fs = FileSystemTools("user-b")
    listing = fs.list_dir(".")
    assert listing["success"] is True
    names = {e["name"] for e in listing["entries"]}
    assert "main.py" in names


def test_local_folder_disabled(runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALLOW_LOCAL_FOLDER", raising=False)
    local = runtime_root / "proj"
    local.mkdir(parents=True)

    with pytest.raises(ValueError, match="未启用"):
        validate_local_folder(str(local))


def test_local_folder_requires_absolute(runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_LOCAL_FOLDER", "1")
    with pytest.raises(ValueError, match="绝对路径"):
        validate_local_folder("relative/path")


def test_reset_to_sandbox(runtime_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_LOCAL_FOLDER", "1")
    local = runtime_root / "proj"
    local.mkdir(parents=True)
    set_local_folder("user-c", str(local))
    info = reset_to_sandbox("user-c")
    assert info["mode"] == "sandbox"
    assert resolve_workspace_root("user-c") == (
        runtime_root / "workspaces" / "user-c" / "projects"
    ).resolve()


def test_workspace_open_folder_api(
    client: TestClient,
    runtime_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOW_LOCAL_FOLDER", "1")
    local = runtime_root / "api-proj"
    local.mkdir()
    (local / "app.py").write_text("# app\n", encoding="utf-8")

    auth = register_user(client, email="folder@example.com")
    headers = auth_headers(auth["access_token"])

    denied = client.post(
        "/api/workspace/open-folder",
        headers=headers,
        json={"path": "relative"},
    )
    assert denied.status_code == 400

    ok = client.post(
        "/api/workspace/open-folder",
        headers=headers,
        json={"path": str(local)},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["mode"] == "local"
    assert body["root"] == str(local.resolve())

    files = client.get("/api/workspace/files", headers=headers)
    assert files.status_code == 200
    paths = {e["path"] for e in files.json()["entries"]}
    assert "app.py" in paths

    reset = client.post("/api/workspace/reset-folder", headers=headers)
    assert reset.status_code == 200
    assert reset.json()["mode"] == "sandbox"
