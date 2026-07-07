"""用户沙箱路径解析（filesystem / search / shell 共用）。"""

from __future__ import annotations

from pathlib import Path

from core.tools.policy import PathPolicy, check_path
from core.user.paths import ensure_user_dirs


class WorkspaceSandbox:
    """限制在用户 runtime/workspaces/{user_id}/projects/ 内。"""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.root = ensure_user_dirs(user_id)
        self._policy = PathPolicy(self.root)

    def resolve(
        self,
        path: str,
        *,
        check_sensitive: bool = True,
    ) -> Path | dict:
        return check_path(path, self.root, check_sensitive=check_sensitive)

    def rel(self, path: Path) -> str:
        return self._policy.rel(path.resolve())
