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


def logs_dir() -> Path:
    return RUNTIME_ROOT / "logs"


def log_file(user_id: str, date_str: str) -> Path:
    return logs_dir() / date_str / f"{user_id}.jsonl"


def admin_dir() -> Path:
    return RUNTIME_ROOT / "admin"


def admin_scripts_dir() -> Path:
    return USER_ROOT / "admin"


def runtime_db_path() -> Path:
    return RUNTIME_ROOT / "db" / "sessions.sqlite"


def ensure_user_dirs(user_id: str) -> Path:
    projects = workspace_projects(user_id)
    sessions = workspace_sessions(user_id)
    projects.mkdir(parents=True, exist_ok=True)
    sessions.mkdir(parents=True, exist_ok=True)
    return projects
