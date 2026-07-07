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
        compact: bool = False,
        emit: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.enabled = enabled
        self.compact = compact
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
        content = (
            f"第 {round_num} 轮 · {tool_count} 个工具"
            if self.compact
            else f"第 {round_num} 轮：调用 {model}，可用工具 {tool_count} 个，分析任务并规划下一步。"
        )
        self._publish(
            ThinkingStep(
                step_type="thought",
                round=round_num,
                index=self._next_index(),
                content=content,
                meta={"model": model, "tool_count": tool_count, "compact": self.compact},
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
        if self.compact:
            status = "成功" if success else "失败"
            self._publish(
                ThinkingStep(
                    step_type="thought",
                    round=round_num,
                    index=self._next_index(),
                    content=f"`{tool_name}` {status}",
                    meta={"tool": tool_name, "success": success, "compact": True},
                )
            )
            self._last_tool = tool_name
            return
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
        if self.compact:
            return
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
    """Max / 深度思考档模型启用完整分步推理可视化。"""
    mid = (model_id or "").lower()
    if not mid or mid == "auto":
        return True  # auto 可能路由到 max
    keys = (
        "qwen-max",
        "qwen3-max",
        "qwen3.7-max",
        "deepseek-v4",
        "glm-5",
    )
    return any(k in mid for k in keys)


def sequential_compact_mode(model_id: str, *, routing: bool = False) -> bool:
    """Flash 等非 Max 模型使用简版 thinking_step。"""
    mid = (model_id or "").lower()
    if routing and (not mid or mid == "auto"):
        return False
    return not model_supports_sequential(mid)
