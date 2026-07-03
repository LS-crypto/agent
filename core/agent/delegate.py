"""子 Agent 委派：主 Loop 将独立子任务交给轻量 Loop 执行。"""

from __future__ import annotations

from typing import Any

from core.agent.loop import AgentLoop
from core.agent.prompts import SUB_AGENT_SYSTEM
from core.tools.registry import ToolRegistry


def delegate_task(
    registry: ToolRegistry,
    *,
    user_id: str,
    task: str,
    max_iterations: int = 8,
) -> tuple[str, list[dict[str, Any]]]:
    """运行只读/探索型子 Agent，返回 (摘要, messages)。"""
    sub = AgentLoop(
        registry,
        user_id=user_id,
        system_prompt=SUB_AGENT_SYSTEM,
        max_iterations=max_iterations,
        enable_routing=False,
        enable_compression=True,
        verbose=False,
    )
    return sub.run(task)
