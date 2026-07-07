"""用户工作区绑定：沙箱 projects/ 或本机目录（阶段 N3）。"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from core.user.paths import user_data_dir, workspace_projects

_BINDING_FILE = "workspace_binding.json"


def is_local_folder_enabled() -> bool:
    return os.getenv("ALLOW_LOCAL_FOLDER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _binding_path(user_id: str) -> Path:
    return user_data_dir(user_id) / _BINDING_FILE


def load_binding(user_id: str) -> dict:
    path = _binding_path(user_id)
    if not path.is_file():
        return {"mode": "sandbox"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"mode": "sandbox"}
    except (json.JSONDecodeError, OSError):
        return {"mode": "sandbox"}


def save_binding(user_id: str, data: dict) -> None:
    user_data_dir(user_id).mkdir(parents=True, exist_ok=True)
    payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
    _binding_path(user_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _blocked_prefixes() -> tuple[str, ...]:
    if sys.platform == "win32":
        return (
            "c:\\windows",
            "c:\\program files",
            "c:\\program files (x86)",
            "c:\\programdata",
        )
    return ("/etc", "/usr", "/bin", "/sbin", "/var", "/root", "/boot", "/proc", "/sys")


def _is_blocked_system_path(resolved: Path) -> bool:
    text = str(resolved).replace("/", "\\").lower().rstrip("\\")
    for prefix in _blocked_prefixes():
        norm = prefix.replace("/", "\\")
        if text == norm or text.startswith(norm + "\\"):
            return True
    return False


def validate_local_folder(path: str) -> Path:
    if not is_local_folder_enabled():
        raise ValueError("当前环境未启用打开本机文件夹（需设置 ALLOW_LOCAL_FOLDER=1）")

    raw = path.strip().strip('"').strip("'")
    if not raw:
        raise ValueError("路径不能为空")

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise ValueError("请填写本机绝对路径，例如 D:\\Projects\\myapp")

    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise ValueError(f"路径无效: {exc}") from exc

    if not resolved.is_dir():
        raise ValueError("路径不存在或不是文件夹")

    if _is_blocked_system_path(resolved):
        raise ValueError("不能绑定系统目录")

    return resolved


def resolve_workspace_root(user_id: str) -> Path:
    """Agent 与工具使用的有效工作区根目录。"""
    binding = load_binding(user_id)
    if binding.get("mode") == "local":
        local_path = binding.get("local_path", "")
        if local_path:
            folder = Path(local_path)
            if folder.is_dir():
                return folder.resolve()

    projects = workspace_projects(user_id)
    projects.mkdir(parents=True, exist_ok=True)
    return projects.resolve()


def get_binding_info(user_id: str) -> dict:
    binding = load_binding(user_id)
    sandbox = workspace_projects(user_id)
    sandbox.mkdir(parents=True, exist_ok=True)
    root = resolve_workspace_root(user_id)
    mode = binding.get("mode", "sandbox")
    if mode != "local":
        mode = "sandbox"
    return {
        "mode": mode,
        "root": str(root),
        "sandbox_path": str(sandbox.resolve()),
        "local_path": binding.get("local_path") if mode == "local" else None,
        "local_folder_enabled": is_local_folder_enabled(),
    }


def set_local_folder(user_id: str, path: str) -> dict:
    resolved = validate_local_folder(path)
    save_binding(
        user_id,
        {"mode": "local", "local_path": str(resolved)},
    )
    return get_binding_info(user_id)


def reset_to_sandbox(user_id: str) -> dict:
    save_binding(user_id, {"mode": "sandbox"})
    return get_binding_info(user_id)
