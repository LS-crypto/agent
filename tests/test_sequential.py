"""Sequential thinking 状态机与 SSE 事件测试。"""

from __future__ import annotations

from core.agent.sequential import (
    SequentialTracker,
    ThinkingStep,
    model_supports_sequential,
    sequential_compact_mode,
)


def test_thinking_step_event():
    step = ThinkingStep(
        step_type="thought",
        content="分析任务",
        round=1,
        index=1,
    )
    ev = step.to_event()
    assert ev["event"] == "thinking_step"
    assert ev["step_type"] == "thought"
    assert ev["round"] == 1


def test_tracker_emits_steps():
    events: list[dict] = []
    tracker = SequentialTracker(enabled=True, emit=events.append)

    tracker.on_round_start(1, 12, "MiniMax-M3")
    tracker.on_tool_decision(1, ["read_file", "grep"])
    tracker.on_tool_result(1, "read_file", True)
    tracker.on_conclusion(1, "这是最终答案。")

    assert len(events) == 4
    assert events[0]["event"] == "thinking_step"
    assert events[-1]["step_type"] == "conclusion"


def test_tracker_disabled():
    events: list[dict] = []
    tracker = SequentialTracker(enabled=False, emit=events.append)
    tracker.on_round_start(1, 5, "MiniMax-M3")
    assert events == []


def test_revision_on_repeat_tool():
    events: list[dict] = []
    tracker = SequentialTracker(enabled=True, emit=events.append)
    tracker.on_tool_result(1, "grep", True)
    tracker.on_tool_result(1, "grep", True)
    assert events[-1]["step_type"] == "revision"


def test_model_supports_sequential():
    # 新接入的旗舰 / 推理模型（替代旧百炼 qwen-max 系列）
    assert model_supports_sequential("MiniMax-M3") is True
    assert model_supports_sequential("deepseek-reasoner") is True
    assert model_supports_sequential("deepseek-v4-pro") is True
    assert model_supports_sequential("glm-5.2") is True
    # 非 Max 模型走 compact 模式
    assert model_supports_sequential("MiniMax-M2.7") is False
    assert model_supports_sequential("deepseek-chat") is False
    assert model_supports_sequential("auto") is True


def test_sequential_compact_mode():
    # flash 模型走 compact；max 模型走完整
    assert sequential_compact_mode("deepseek-chat") is True
    assert sequential_compact_mode("MiniMax-M3") is False
    assert sequential_compact_mode("auto", routing=True) is False


def test_tracker_compact_skips_conclusion():
    events: list[dict] = []
    tracker = SequentialTracker(enabled=True, compact=True, emit=events.append)
    tracker.on_round_start(1, 8, "deepseek-chat")
    tracker.on_tool_decision(1, ["write_file"])
    tracker.on_tool_result(1, "write_file", True)
    tracker.on_conclusion(1, "完成")
    assert len(events) == 3
    assert events[0]["content"] == "第 1 轮 · 8 个工具"
    assert events[-1]["content"] == "`write_file` 成功"
