"""工作区 zip 上传解压（ECS 云端沙箱 · 替代「打开本机文件夹」）。"""

from __future__ import annotations

import io
import os
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from core.tools.policy import is_sensitive_path
from core.tools.quota import (
    _human_bytes,
    get_quota_limit_bytes,
    quota_summary,
    workspace_usage_bytes,
)
from core.user.paths import workspace_projects
from core.user.workspace_binding import load_binding, reset_to_sandbox

MAX_ZIP_BYTES = int(os.getenv("WORKSPACE_UPLOAD_MAX_ZIP_BYTES", str(50 * 1024 * 1024)))
MAX_FILES = int(os.getenv("WORKSPACE_UPLOAD_MAX_FILES", "2000"))
MAX_SINGLE_FILE = int(os.getenv("WORKSPACE_UPLOAD_MAX_FILE_BYTES", str(10 * 1024 * 1024)))
MAX_LISTING_ENTRIES = 200


class WorkspaceUploadError(ValueError):
    """客户端可修复的上传错误。"""


class WorkspaceQuotaError(WorkspaceUploadError):
    """超出工作区配额。"""


@dataclass
class ZipMember:
    rel_path: str
    data: bytes
    is_dir: bool = False


@dataclass
class UploadResult:
    mode: str
    target_dir: str | None
    files_written: int
    bytes_written: int
    skipped_files: int
    skipped_reasons: list[str] = field(default_factory=list)
    entries: list[dict] = field(default_factory=list)
    truncated_listing: bool = False
    root_entry: str | None = None
    switched_to_sandbox: bool = False


def upload_enabled() -> bool:
    return os.getenv("WORKSPACE_UPLOAD_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _safe_zip_rel(name: str) -> str | None:
    normalized = name.replace("\\", "/").strip()
    if not normalized:
        return None
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return None
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if ".." in parts:
        return None
    return "/".join(parts)


def validate_target_dir(target_dir: str | None) -> str:
    raw = (target_dir or "").strip().strip("/")
    if not raw or raw == ".":
        return "."
    parts = [p for p in raw.replace("\\", "/").split("/") if p and p != "."]
    if ".." in parts:
        raise WorkspaceUploadError("target_dir 非法")
    if not parts:
        return "."
    return "/".join(parts)


def _parse_zip(raw: bytes) -> list[ZipMember]:
    if len(raw) > MAX_ZIP_BYTES:
        raise WorkspaceUploadError(
            f"zip 文件过大（上限 {_human_bytes(MAX_ZIP_BYTES)}）"
        )
    if len(raw) < 4:
        raise WorkspaceUploadError("无法解压：文件不是有效的 zip")

    members: list[ZipMember] = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for info in zf.infolist():
                rel = _safe_zip_rel(info.filename)
                if rel is None:
                    raise WorkspaceUploadError("包内含有非法路径，已拒绝")
                if info.is_dir() or rel.endswith("/"):
                    rel = rel.rstrip("/")
                    if rel:
                        members.append(ZipMember(rel_path=rel, data=b"", is_dir=True))
                    continue
                if info.file_size > MAX_SINGLE_FILE:
                    raise WorkspaceUploadError(
                        f"包内文件 {rel} 过大（单文件上限 {_human_bytes(MAX_SINGLE_FILE)}）"
                    )
                data = zf.read(info)
                if len(data) > MAX_SINGLE_FILE:
                    raise WorkspaceUploadError(
                        f"包内文件 {rel} 过大（单文件上限 {_human_bytes(MAX_SINGLE_FILE)}）"
                    )
                members.append(ZipMember(rel_path=rel, data=data))
    except zipfile.BadZipFile as exc:
        raise WorkspaceUploadError("无法解压：文件不是有效的 zip") from exc

    file_members = [m for m in members if not m.is_dir]
    if len(file_members) > MAX_FILES:
        raise WorkspaceUploadError(f"包内文件过多（上限 {MAX_FILES} 个）")
    if not file_members:
        raise WorkspaceUploadError("zip 内没有可导入的文件")

    return members


def _strip_single_root(members: list[ZipMember]) -> tuple[list[ZipMember], str | None]:
    file_paths = [m.rel_path for m in members if not m.is_dir]
    if not file_paths:
        return members, None

    tops: set[str] = set()
    for path in file_paths:
        tops.add(path.split("/")[0])

    if len(tops) != 1:
        return members, None

    root = next(iter(tops))
    prefix = root + "/"
    if not all(p == root or p.startswith(prefix) for p in file_paths):
        return members, None

    stripped: list[ZipMember] = []
    for member in members:
        if member.is_dir:
            if member.rel_path == root:
                continue
            if member.rel_path.startswith(prefix):
                stripped.append(
                    ZipMember(
                        rel_path=member.rel_path[len(prefix) :],
                        data=member.data,
                        is_dir=True,
                    )
                )
            continue
        if member.rel_path == root:
            continue
        if member.rel_path.startswith(prefix):
            stripped.append(
                ZipMember(
                    rel_path=member.rel_path[len(prefix) :],
                    data=member.data,
                )
            )
        else:
            return members, None

    if not any(not m.is_dir for m in stripped):
        return members, None
    return stripped, root


def _clear_directory(path: Path) -> None:
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=True)
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)


def _estimate_bytes(members: list[ZipMember]) -> int:
    return sum(len(m.data) for m in members if not m.is_dir)


def _check_quota(user_id: str, members: list[ZipMember], *, replace: bool) -> None:
    extra = _estimate_bytes(members)
    if get_quota_limit_bytes() is None:
        return

    projects = workspace_projects(user_id).resolve()
    if replace:
        projected = extra
    else:
        used = workspace_usage_bytes(projects)
        projected = used + extra

    limit = get_quota_limit_bytes()
    assert limit is not None
    if projected <= limit:
        return

    if replace:
        msg = (
            f"解压后将超过工作区配额（需要 {_human_bytes(extra)}，"
            f"上限 {_human_bytes(limit)}）"
        )
    else:
        used = workspace_usage_bytes(projects)
        remaining = max(0, limit - used)
        msg = (
            f"解压后将超过工作区配额（需要 {_human_bytes(extra)}，"
            f"剩余 {_human_bytes(remaining)}）"
        )
    raise WorkspaceQuotaError(msg)


def _write_members(
    dest_root: Path,
    members: list[ZipMember],
) -> tuple[int, int, int, list[str], list[dict]]:
    files_written = 0
    bytes_written = 0
    skipped = 0
    skipped_reasons: list[str] = []
    entries: list[dict] = []

    dest_root.mkdir(parents=True, exist_ok=True)

    for member in members:
        if member.is_dir:
            (dest_root / member.rel_path).mkdir(parents=True, exist_ok=True)
            continue

        rel = member.rel_path
        if is_sensitive_path(rel):
            skipped += 1
            if len(skipped_reasons) < 10:
                skipped_reasons.append(f"skipped sensitive: {rel}")
            continue

        target = dest_root / rel
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(member.data)
        except OSError as exc:
            skipped += 1
            if len(skipped_reasons) < 10:
                skipped_reasons.append(f"write failed {rel}: {exc}")
            continue

        files_written += 1
        bytes_written += len(member.data)
        if len(entries) < MAX_LISTING_ENTRIES:
            entries.append(
                {
                    "path": rel.replace("\\", "/"),
                    "name": Path(rel).name,
                    "type": "file",
                    "size": len(member.data),
                }
            )

    truncated = files_written > MAX_LISTING_ENTRIES
    return files_written, bytes_written, skipped, skipped_reasons, entries


def _guess_root_entry(entries: list[dict]) -> str | None:
    if not entries:
        return None
    tops: set[str] = set()
    for entry in entries:
        path = entry["path"]
        tops.add(path.split("/")[0])
    if len(tops) == 1:
        top = next(iter(tops))
        if any(e["path"] == top for e in entries):
            return top
        return top
    return entries[0]["path"]


def upload_workspace_zip(
    user_id: str,
    raw: bytes,
    *,
    mode: str = "merge",
    target_dir: str | None = None,
    strip_root: bool = True,
) -> UploadResult:
    if not upload_enabled():
        raise WorkspaceUploadError("工作区上传功能已关闭")

    if mode not in ("merge", "subdir", "replace"):
        raise WorkspaceUploadError("mode 必须是 merge、subdir 或 replace")

    rel_target = validate_target_dir(target_dir if mode == "subdir" else None)
    members = _parse_zip(raw)

    stripped_root: str | None = None
    if strip_root:
        members, stripped_root = _strip_single_root(members)

    _check_quota(user_id, members, replace=mode == "replace")

    projects = workspace_projects(user_id).resolve()
    projects.mkdir(parents=True, exist_ok=True)

    if mode == "replace":
        _clear_directory(projects)
        dest_root = projects
        api_target_dir: str | None = "."
    elif mode == "subdir":
        dest_root = projects / rel_target if rel_target != "." else projects
        if dest_root.resolve() != projects.resolve():
            try:
                dest_root.resolve().relative_to(projects.resolve())
            except ValueError as exc:
                raise WorkspaceUploadError("target_dir 非法") from exc
        api_target_dir = rel_target
    else:
        dest_root = projects
        api_target_dir = "."

    was_local = load_binding(user_id).get("mode") == "local"
    switched = False
    if was_local:
        reset_to_sandbox(user_id)
        switched = True

    files_written, bytes_written, skipped, skipped_reasons, entries = _write_members(
        dest_root,
        members,
    )

    root_entry = stripped_root or _guess_root_entry(entries)

    return UploadResult(
        mode=mode,
        target_dir=api_target_dir,
        files_written=files_written,
        bytes_written=bytes_written,
        skipped_files=skipped,
        skipped_reasons=skipped_reasons,
        entries=entries,
        truncated_listing=files_written > MAX_LISTING_ENTRIES,
        root_entry=root_entry,
        switched_to_sandbox=switched,
    )


def upload_response_payload(user_id: str, result: UploadResult) -> dict:
    return {
        "success": True,
        "mode": result.mode,
        "target_dir": result.target_dir,
        "files_written": result.files_written,
        "bytes_written": result.bytes_written,
        "total_size": _human_bytes(result.bytes_written),
        "skipped_files": result.skipped_files,
        "skipped_reasons": result.skipped_reasons,
        "truncated_listing": result.truncated_listing,
        "entries": result.entries,
        "quota": quota_summary(user_id),
        "root_entry": result.root_entry,
        "switched_to_sandbox": result.switched_to_sandbox,
    }
