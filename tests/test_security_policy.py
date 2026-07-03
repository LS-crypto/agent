"""工具层安全策略测试。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.tools.filesystem import FileSystemTools
from core.tools.policy import (
    check_path,
    check_shell,
    is_sensitive_path,
)
from core.tools.shell import ShellTools


@pytest.fixture
def sandbox_root(tmp_path: Path) -> Path:
    root = tmp_path / "projects"
    root.mkdir()
    return root


@pytest.fixture
def fs_tools(sandbox_root: Path, monkeypatch: pytest.MonkeyPatch) -> FileSystemTools:
    monkeypatch.setattr(
        "core.tools.sandbox.ensure_user_dirs",
        lambda _uid: sandbox_root,
    )
    return FileSystemTools("test-user")


@pytest.fixture
def shell_tools(sandbox_root: Path, monkeypatch: pytest.MonkeyPatch) -> ShellTools:
    monkeypatch.setattr(
        "core.tools.sandbox.ensure_user_dirs",
        lambda _uid: sandbox_root,
    )
    return ShellTools("test-user")


class TestPathPolicy:
    def test_traversal_rejected(self, sandbox_root: Path) -> None:
        result = check_path("../../../etc/passwd", sandbox_root)
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["policy"] == "path_blocked"

    def test_normal_file_allowed(self, sandbox_root: Path) -> None:
        target = sandbox_root / "foo" / "bar.txt"
        target.parent.mkdir(parents=True)
        target.write_text("ok", encoding="utf-8")

        result = check_path("foo/bar.txt", sandbox_root)
        assert isinstance(result, Path)
        assert result.name == "bar.txt"

    def test_sensitive_env_rejected(self, sandbox_root: Path) -> None:
        env_file = sandbox_root / ".env"
        env_file.write_text("KEY=1", encoding="utf-8")

        result = check_path(".env", sandbox_root, check_sensitive=True)
        assert isinstance(result, dict)
        assert result["policy"] == "sensitive_file"

    def test_symlink_escape_rejected(
        self, sandbox_root: Path, tmp_path: Path
    ) -> None:
        outside = tmp_path / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        link = sandbox_root / "link.txt"
        link.symlink_to(outside)

        result = check_path("link.txt", sandbox_root, check_sensitive=False)
        assert isinstance(result, dict)
        assert result["policy"] == "symlink_escape"


class TestSensitivePaths:
    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            ".env.local",
            "keys/server.pem",
            "id_rsa",
            "my_credentials.json",
            "client_secret.txt",
            ".git/config",
        ],
    )
    def test_sensitive(self, path: str) -> None:
        assert is_sensitive_path(path) is True

    def test_readme_allowed(self) -> None:
        assert is_sensitive_path("readme.txt") is False


class TestShellPolicy:
    def test_python_c_rejected(self) -> None:
        err = check_shell('python -c "print(1)"')
        assert err is not None
        assert "python -c" in err

    def test_python_script_allowed(self) -> None:
        assert check_shell("python hello.py") is None

    def test_dir_allowed(self) -> None:
        assert check_shell("dir") is None
        assert check_shell("ls -la") is None

    def test_git_push_rejected(self) -> None:
        err = check_shell("git push origin main")
        assert err is not None

    def test_git_status_allowed(self) -> None:
        assert check_shell("git status") is None


class TestFileSystemIntegration:
    def test_read_env_rejected(self, fs_tools: FileSystemTools, sandbox_root: Path) -> None:
        (sandbox_root / ".env").write_text("SECRET=1", encoding="utf-8")
        result = fs_tools.read_file(".env")
        assert result["success"] is False
        assert result["policy"] == "sensitive_file"

    def test_read_readme_ok(self, fs_tools: FileSystemTools, sandbox_root: Path) -> None:
        (sandbox_root / "readme.txt").write_text("hello", encoding="utf-8")
        result = fs_tools.read_file("readme.txt")
        assert result["success"] is True
        assert result["content"] == "hello"

    def test_write_env_rejected(self, fs_tools: FileSystemTools) -> None:
        result = fs_tools.write_file(".env", "X=1")
        assert result["success"] is False
        assert result["policy"] == "sensitive_file"

    def test_list_dir_hides_sensitive(
        self, fs_tools: FileSystemTools, sandbox_root: Path
    ) -> None:
        (sandbox_root / ".env").write_text("X=1", encoding="utf-8")
        (sandbox_root / "readme.txt").write_text("ok", encoding="utf-8")
        result = fs_tools.list_dir(".")
        assert result["success"] is True
        names = {e["name"] for e in result["entries"]}
        assert ".env" not in names
        assert "readme.txt" in names


class TestShellIntegration:
    def test_execute_python_c_blocked(self, shell_tools: ShellTools) -> None:
        result = shell_tools.execute_command('python -c "print(1)"')
        assert result["success"] is False
        assert result.get("policy") == "shell_blocked"

    @pytest.mark.skipif(
        os.name != "nt",
        reason="Windows dir 命令",
    )
    def test_execute_dir_allowed(self, shell_tools: ShellTools) -> None:
        result = shell_tools.execute_command("dir")
        assert "policy" not in result or result.get("policy") != "shell_blocked"
