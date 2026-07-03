"""Max 模型分步推理状态机：thought / revision / conclusion → SSE thinking_step。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

StepType = Literal["thought", "revision", "conclusion"]


@dataclass
class ThinkingStep:
    step_type: StepType
    content: str
    round: int = 0
    index: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_event(self) -> dict[str, Any]:
        return {
            "event": "thinking_step",
            "step_type": self.step_type,
            "content": self.content,
            "round": self.round,
            "index": self.index,
            **self.meta,
        }


class SequentialTracker:
    """在 Agent Loop 各阶段发射 thinking_step 事件。"""

    def __init__(
        self,
        *,
        enabled: bool = True,
        emit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.enabled = enabled
        self._emit = emit
        self._index = 0
        self._last_tool: str | None = None
        self._tool_counts: dict[str, int] = {}

    def _next_index(self) -> int:
        self._index += 1
        return self._index

    def _publish(self, step: ThinkingStep) -> None:
        if not self.enabled or not self._emit:
            return
        self._emit(step.to_event())

    def on_round_start(self, round_num: int, tool_count: int, model: str) -> None:
        self._publish(
            ThinkingStep(
                step_type="thought",
                round=round_num,
                index=self._next_index(),
                content=f"第 {round_num} 轮：调用 {model}，可用工具 {tool_count} 个，分析任务并规划下一步。",
                meta={"model": model, "tool_count": tool_count},
            )
        )

    def on_tool_decision(self, round_num: int, tool_names: list[str]) -> None:
        names = ", ".join(tool_names[:5])
        if len(tool_names) > 5:
            names += f" 等 {len(tool_names)} 个"
        self._publish(
            ThinkingStep(
                step_type="thought",
                round=round_num,
                index=self._next_index(),
                content=f"决定调用工具：{names}",
                meta={"tools": tool_names},
            )
        )

    def on_tool_result(self, round_num: int, tool_name: str, success: bool) -> None:
        count = self._tool_counts.get(tool_name, 0) + 1
        self._tool_counts[tool_name] = count
        step_type: StepType = "revision" if count > 1 or (
            self._last_tool == tool_name and count > 1
        ) else "thought"
        status = "成功" if success else "失败"
        self._publish(
            ThinkingStep(
                step_type=step_type,
                round=round_num,
                index=self._next_index(),
                content=f"工具 `{tool_name}` 执行{status}，整合结果继续推理。",
                meta={"tool": tool_name, "success": success, "repeat": count},
            )
        )
        self._last_tool = tool_name

    def on_conclusion(self, round_num: int, preview: str) -> None:
        text = preview.strip()
        if len(text) > 200:
            text = text[:200] + "…"
        self._publish(
            ThinkingStep(
                step_type="conclusion",
                round=round_num,
                index=self._next_index(),
                content=text or "生成最终回复。",
            )
        )


def model_supports_sequential(model_id: str) -> bool:
    """Max 档模型启用分步推理可视化。"""
    mid = (model_id or "").lower()
    if not mid or mid == "auto":
        return True  # auto 可能路由到 max
    return any(k in mid for k in ("qwen-max", "qwen3-max", "max"))
