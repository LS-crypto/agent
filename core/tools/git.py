"""Git 工具：status / diff / commit（review 级，沙箱内）。"""

from __future__ import annotations

import subprocess

from core.tools.registry import ToolRegistry
from core.tools.sandbox import WorkspaceSandbox


class GitTools:
    def __init__(self, user_id: str) -> None:
        self.sandbox = WorkspaceSandbox(user_id)

    def _run(self, args: list[str]) -> dict:
        cwd = str(self.sandbox.root.resolve())
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            output = (result.stdout or "").strip()
            if result.stderr:
                output = f"{output}\n[stderr]\n{result.stderr.strip()}".strip()
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": output[:8000],
            }
        except FileNotFoundError:
            return {"success": False, "error": "未安装 git"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "git 命令超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def git_status(self) -> dict:
        return self._run(["status", "--short"])

    def git_diff(self, staged: bool = False) -> dict:
        args = ["diff", "--stat"]
        if staged:
            args.insert(1, "--cached")
        return self._run(args)

    def git_commit(self, message: str) -> dict:
        if not message.strip():
            return {"success": False, "error": "commit message 不能为空"}
        return self._run(["commit", "-m", message.strip()])


def register_git_tools(registry: ToolRegistry, user_id: str) -> None:
    git = GitTools(user_id)
    registry.register(
        name="git_status",
        description="查看沙箱项目 git 状态（short format）。",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda: git.git_status(),
    )
    registry.register(
        name="git_diff",
        description="查看 git diff 统计。staged=true 时查看暂存区。",
        parameters={
            "type": "object",
            "properties": {
                "staged": {"type": "boolean", "description": "是否只看 staged"},
            },
            "required": [],
        },
        handler=git.git_diff,
    )
    registry.register(
        name="git_commit",
        description="提交已暂存更改。需用户确认。message 为提交说明。",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "commit message"},
            },
            "required": ["message"],
        },
        handler=git.git_commit,
    )
