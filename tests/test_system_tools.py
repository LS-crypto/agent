"""系统信息工具测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.tools.system import SystemTools


@pytest.fixture
def sys_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SystemTools:
    root = tmp_path / "projects"
    root.mkdir()
    (root / "a.txt").write_text("hello", encoding="utf-8")
    monkeypatch.setattr(
        "core.tools.sandbox.ensure_user_dirs",
        lambda _uid: root,
    )
    return SystemTools("test-user")


def test_get_disk_usage(sys_tools: SystemTools) -> None:
    r = sys_tools.get_disk_usage(".")
    assert r["success"] is True
    assert r["total_bytes"] > 0
    assert "free" in r


def test_get_workspace_stats(sys_tools: SystemTools) -> None:
    r = sys_tools.get_workspace_stats()
    assert r["success"] is True
    assert r["file_count"] >= 1


def test_get_env_info(sys_tools: SystemTools) -> None:
    r = sys_tools.get_env_info()
    assert r["success"] is True
    assert "python" in r
