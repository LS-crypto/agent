"""工作区 zip 上传测试。"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.user.paths import workspace_projects
from server.services.workspace_upload import (
    WorkspaceQuotaError,
    WorkspaceUploadError,
    upload_workspace_zip,
)
from tests.conftest import auth_headers, register_user


def _make_zip(files: dict[str, str | bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            zf.writestr(name, content)
    return buf.getvalue()


def test_upload_merge_simple(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="up@example.com")
    user_id = auth["user"]["id"]
    headers = auth_headers(auth["access_token"])

    raw = _make_zip({"hello.py": "print('hi')\n", "src/main.py": "x = 1\n"})
    res = client.post(
        "/api/workspace/upload",
        headers=headers,
        files={"file": ("proj.zip", raw, "application/zip")},
        data={"mode": "merge", "strip_root": "true"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["files_written"] == 2
    assert (workspace_projects(user_id) / "hello.py").is_file()
    assert (workspace_projects(user_id) / "src" / "main.py").is_file()


def test_upload_strip_root(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="strip@example.com")
    user_id = auth["user"]["id"]
    headers = auth_headers(auth["access_token"])

    raw = _make_zip({"my-app/app.py": "1\n", "my-app/readme.md": "hi\n"})
    res = client.post(
        "/api/workspace/upload",
        headers=headers,
        files={"file": ("proj.zip", raw, "application/zip")},
        data={"strip_root": "true"},
    )
    assert res.status_code == 200
    assert (workspace_projects(user_id) / "app.py").is_file()
    assert res.json()["root_entry"] == "my-app"


def test_upload_subdir_mode(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="subdir@example.com")
    user_id = auth["user"]["id"]
    headers = auth_headers(auth["access_token"])

    raw = _make_zip({"a.txt": "a\n"})
    res = client.post(
        "/api/workspace/upload",
        headers=headers,
        files={"file": ("proj.zip", raw, "application/zip")},
        data={"mode": "subdir", "target_dir": "imported"},
    )
    assert res.status_code == 200
    assert (workspace_projects(user_id) / "imported" / "a.txt").is_file()


def test_upload_replace_clears_old(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="repl@example.com")
    user_id = auth["user"]["id"]
    headers = auth_headers(auth["access_token"])
    projects = workspace_projects(user_id)
    projects.mkdir(parents=True, exist_ok=True)
    (projects / "old.txt").write_text("old", encoding="utf-8")

    raw = _make_zip({"new.txt": "new\n"})
    res = client.post(
        "/api/workspace/upload",
        headers=headers,
        files={"file": ("proj.zip", raw, "application/zip")},
        data={"mode": "replace"},
    )
    assert res.status_code == 200
    assert not (projects / "old.txt").exists()
    assert (projects / "new.txt").read_text(encoding="utf-8") == "new\n"


def test_upload_rejects_zip_slip(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="slip@example.com")
    headers = auth_headers(auth["access_token"])

    raw = _make_zip({"../evil.txt": "bad\n"})
    res = client.post(
        "/api/workspace/upload",
        headers=headers,
        files={"file": ("bad.zip", raw, "application/zip")},
    )
    assert res.status_code == 400


def test_upload_skips_sensitive_env(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="env@example.com")
    user_id = auth["user"]["id"]
    headers = auth_headers(auth["access_token"])

    raw = _make_zip({".env": "SECRET=1\n", "ok.py": "pass\n"})
    res = client.post(
        "/api/workspace/upload",
        headers=headers,
        files={"file": ("proj.zip", raw, "application/zip")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["files_written"] == 1
    assert body["skipped_files"] == 1
    assert not (workspace_projects(user_id) / ".env").exists()
    assert (workspace_projects(user_id) / "ok.py").is_file()


def test_upload_quota_exceeded(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setenv("USER_WORKSPACE_QUOTA_BYTES", "20")

    auth = register_user(client, email="quota@example.com")
    headers = auth_headers(auth["access_token"])

    raw = _make_zip({"big.txt": "x" * 50})
    res = client.post(
        "/api/workspace/upload",
        headers=headers,
        files={"file": ("big.zip", raw, "application/zip")},
    )
    assert res.status_code == 413


def test_upload_requires_auth(client: TestClient) -> None:
    raw = _make_zip({"a.txt": "a\n"})
    res = client.post(
        "/api/workspace/upload",
        files={"file": ("a.zip", raw, "application/zip")},
    )
    assert res.status_code == 401


def test_upload_rejects_non_zip(client: TestClient, tmp_path, monkeypatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    auth = register_user(client, email="type@example.com")
    headers = auth_headers(auth["access_token"])

    res = client.post(
        "/api/workspace/upload",
        headers=headers,
        files={"file": ("readme.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 400


def test_upload_service_unit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = tmp_path / "runtime"
    monkeypatch.setattr("core.paths.RUNTIME_ROOT", runtime)
    monkeypatch.setattr("core.user.paths.RUNTIME_ROOT", runtime)

    raw = _make_zip({"a/b.txt": "hi\n"})
    result = upload_workspace_zip("u-unit", raw, mode="merge")
    assert result.files_written == 1

    with pytest.raises(WorkspaceUploadError):
        upload_workspace_zip("u-unit", b"not-a-zip", mode="merge")

    monkeypatch.setenv("USER_WORKSPACE_QUOTA_BYTES", "5")
    with pytest.raises(WorkspaceQuotaError):
        upload_workspace_zip("u-unit", _make_zip({"huge.txt": "x" * 20}), mode="merge")
