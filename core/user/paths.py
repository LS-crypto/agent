"""路径工具：源码与 runtime/ 分离。"""

from pathlib import Path

from core.paths import CORE_ROOT, PROJECT_ROOT, RUNTIME_ROOT

USER_ROOT = CORE_ROOT / "user"


def runtime_root() -> Path:
    return RUNTIME_ROOT


def workspace_projects(user_id: str) -> Path:
    return RUNTIME_ROOT / "workspaces" / user_id / "projects"


def workspace_sessions(user_id: str) -> Path:
    return RUNTIME_ROOT / "workspaces" / user_id / "sessions"


def user_data_dir(user_id: str) -> Path:
    return RUNTIME_ROOT / "workspaces" / user_id / "data"


def user_db_path(user_id: str) -> Path:
    """每用户独立会话数据库。"""
    return user_data_dir(user_id) / "sessions.sqlite"


def logs_dir() -> Path:
    return RUNTIME_ROOT / "logs"


def log_file(user_id: str, date_str: str) -> Path:
    return logs_dir() / date_str / f"{user_id}.jsonl"


def admin_dir() -> Path:
    return RUNTIME_ROOT / "admin"


def admin_scripts_dir() -> Path:
    return USER_ROOT / "admin"


def runtime_db_path() -> Path:
    """全局认证库（用户账号 + 加密 API Key），不含会话。"""
    return RUNTIME_ROOT / "db" / "auth.sqlite"


def legacy_runtime_db_path() -> Path:
    """升级前单库路径（仅用于迁移）。"""
    return RUNTIME_ROOT / "db" / "sessions.sqlite"


def ensure_user_dirs(user_id: str) -> Path:
    projects = workspace_projects(user_id)
    sessions = workspace_sessions(user_id)
    data = user_data_dir(user_id)
    projects.mkdir(parents=True, exist_ok=True)
    sessions.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    from core.user.workspace_binding import resolve_workspace_root

    return resolve_workspace_root(user_id)
