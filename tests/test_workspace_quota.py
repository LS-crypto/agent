"""工作区磁盘配额测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.tools.filesystem import FileSystemTools
from core.tools.quota import check_workspace_quota, get_quota_limit_bytes, quota_summary


@pytest.fixture
def projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr(
        "core.tools.sandbox.ensure_user_dirs",
        lambda _uid: root,
    )
    monkeypatch.setattr(
        "core.tools.quota.ensure_user_dirs",
        lambda _uid: root,
    )
    monkeypatch.setattr(
        "core.tools.quota.workspace_projects",
        lambda _uid: root,
    )
    return root


def test_quota_blocks_write_when_full(projects: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_WORKSPACE_QUOTA_BYTES", "50")
    (projects / "big.txt").write_bytes(b"x" * 40)

    fs = FileSystemTools("u1")
    result = fs.write_file("new.txt", "abcdefghijklmnop")  # 16 bytes, 40+16>50

    assert result["success"] is False
    assert result["policy"] == "workspace_quota"


def test_quota_allows_write_under_limit(projects: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_WORKSPACE_QUOTA_BYTES", "100")
    fs = FileSystemTools("u1")
    result = fs.write_file("ok.txt", "hello")

    assert result["success"] is True
    assert (projects / "ok.txt").read_text(encoding="utf-8") == "hello"


def test_quota_zero_means_unlimited(projects: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_WORKSPACE_QUOTA_BYTES", "0")
    assert get_quota_limit_bytes() is None

    fs = FileSystemTools("u1")
    big = "x" * 200_000
    result = fs.write_file("huge.txt", big)

    assert result["success"] is True


def test_quota_overwrite_counts_delta(projects: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_WORKSPACE_QUOTA_BYTES", "30")
    target = projects / "a.txt"
    target.write_bytes(b"12345")  # 5 bytes

    fs = FileSystemTools("u1")
    ok = fs.write_file("a.txt", "12345678901234567890")  # 20 bytes total
    assert ok["success"] is True

    over = fs.write_file("b.txt", "x" * 20)  # 20+20=40 > 30
    assert over["success"] is False
    assert over["policy"] == "workspace_quota"


def test_quota_summary_fields(projects: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_WORKSPACE_QUOTA_BYTES", "100")
    (projects / "f.txt").write_bytes(b"abc")

    summary = quota_summary("u1")

    assert summary["quota_bytes"] == 100
    assert summary["quota_remaining_bytes"] == 97
    assert summary["quota_percent_used"] == 3.0


def test_check_workspace_quota_replace_path(projects: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_WORKSPACE_QUOTA_BYTES", "20")
    fp = projects / "old.txt"
    fp.write_bytes(b"1234567890")  # 10

    err = check_workspace_quota("u1", extra_bytes=15, replace_path=fp)
    assert err is None  # 10 - 10 + 15 = 15 <= 20

    err2 = check_workspace_quota("u1", extra_bytes=25, replace_path=fp)
    assert err2 is not None
    assert err2["policy"] == "workspace_quota"
