"""终端命令工具：在沙箱目录内执行，带 ShellPolicy 校验。"""

from __future__ import annotations

import subprocess

from core.agent.permissions import get_permission_tier
from core.tools.policy import DEFAULT_SHELL_TIMEOUT, check_shell
from core.tools.registry import ToolRegistry
from core.tools.sandbox import WorkspaceSandbox


class ShellTools:
    def __init__(self, user_id: str) -> None:
        self.sandbox = WorkspaceSandbox(user_id)

    def execute_command(
        self,
        command: str,
        timeout: int = DEFAULT_SHELL_TIMEOUT,
    ) -> dict:
        blocked = check_shell(command, tier=get_permission_tier())
        if blocked:
            return {"success": False, "error": blocked, "policy": "shell_blocked"}

        cwd = str(self.sandbox.root.resolve())
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            output = stdout
            if stderr:
                output = f"{stdout}\n[stderr]\n{stderr}".strip() if stdout else stderr
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "output": output[:8000],
                "cwd": cwd,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"命令执行超时 ({timeout}s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def register_shell_tools(registry: ToolRegistry, user_id: str) -> None:
    shell = ShellTools(user_id)
    registry.register(
        name="execute_command",
        description=(
            "在用户沙箱项目根目录执行 shell 命令并返回输出。"
            "白名单: python/pytest/pip、dir/ls/cat、git status/diff/log 等。"
            "禁止 python -c、curl、sudo、绝对路径与危险删除命令。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"},
                "timeout": {
                    "type": "integer",
                    "description": "超时秒数，默认 30",
                },
            },
            "required": ["command"],
        },
        handler=shell.execute_command,
    )
