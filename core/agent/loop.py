"""通用 Agentic Loop：模型推理 + 工具调用循环。"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from openai import OpenAI

from core.agent.activity import ActivityLogger
from core.agent.permissions import PermissionTier
from core.agent.compressor import ToolResultCompressor
from core.agent.console import out, step, warn
from core.agent.router import route, route_by_tool_call
from core.agent.sequential import SequentialTracker
from core.agent.tool_gate import run_tool_with_policy
from core.config import MODEL_CODER, create_client, get_model_name
from core.tools.registry import ToolRegistry


class AgentLoop:
    """Agent 主循环：发送 messages → 模型决策 → 执行工具 → 回传结果。

    支持动态模型路由：首轮根据用户输入路由，后续轮根据工具调用类型调整模型。
    支持工具结果压缩：工具输出在送入上下文前智能裁剪，减少 token 消耗。
    """

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        user_id: str = "default",
        model: str = MODEL_CODER,
        system_prompt: str | None = None,
        max_iterations: int = 15,
        temperature: float = 0.2,
        client: OpenAI | None = None,
        activity: ActivityLogger | None = None,
        verbose: bool = False,
        enable_routing: bool = True,
        enable_compression: bool = True,
        permission_tier: PermissionTier = "balanced",
        sequential: SequentialTracker | None = None,
    ) -> None:
        self.registry = registry
        self.user_id = user_id
        self.model = model
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.client = client or create_client()
        self.verbose = verbose
        self.activity = activity or ActivityLogger(user_id, mirror_console=verbose)
        self.enable_routing = enable_routing
        self.enable_compression = enable_compression
        self.permission_tier = permission_tier
        self.sequential = sequential
        self._compressor = ToolResultCompressor()

    def _initial_messages(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        return messages

    def _trace(self, title: str, note: str) -> None:
        if self.verbose:
            step(title, note)

    def _select_model(self, user_input: str, round_num: int, last_tool: str | None = None) -> str:
        """选择当前轮次使用的模型。"""
        if not self.enable_routing:
            return self.model

        # 首轮：根据用户输入路由
        if round_num == 1:
            complexity, model_name = route(user_input, use_llm=True)
            self._trace("模型路由", f"复杂度={complexity}，模型={model_name}")
            return model_name

        # 后续轮：根据上一次工具调用类型调整
        if last_tool:
            tier = route_by_tool_call(last_tool, {})
            model_name = get_model_name(tier)
            self._trace("模型路由", f"工具={last_tool}，tier={tier}，模型={model_name}")
            return model_name

        return self.model

    def run(
        self,
        user_input: str,
        messages: list[dict[str, Any]] | None = None,
        *,
        confirm_handler: Callable[[str, dict[str, Any]], bool] | None = None,
        session_id: str | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """执行一轮用户请求，返回 (最终回复, 更新后的 messages)。"""
        if messages is None:
            messages = self._initial_messages()

        rate_key = f"{self.user_id}:{session_id or 'cli'}"

        self._trace("Agent 启动", f"用户 {self.user_id}，model={self.model}")
        self.activity.user_message(user_input)
        messages.append({"role": "user", "content": user_input})

        tool_count = len(self.registry.get_schemas())
        last_tool: str | None = None

        for round_num in range(1, self.max_iterations + 1):
            self.activity.loop_round(round_num, tool_count)

            # 动态选择模型
            current_model = self._select_model(user_input, round_num, last_tool)

            if self.sequential:
                self.sequential.on_round_start(round_num, tool_count, current_model)

            self._trace(
                f"第 {round_num} 轮 · 请求模型",
                f"model={current_model}，发送 messages 与 {tool_count} 个工具定义",
            )

            try:
                resp = self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    tools=self.registry.get_schemas(),
                    tool_choice="auto",
                    temperature=self.temperature,
                )
            except Exception as e:
                self.activity.error(str(e))
                if self.verbose:
                    warn(str(e), "百炼 API 请求失败")
                return f"API 错误: {e}", messages

            msg = resp.choices[0].message

            if not msg.tool_calls:
                self._trace("模型返回最终答案", "无 tool_calls，循环结束")
                final = msg.content or ""
                if self.sequential:
                    self.sequential.on_conclusion(round_num, final)
                messages.append(msg.model_dump())
                self.activity.assistant_reply(final)
                return final, messages

            self.activity.model_tool_decision(len(msg.tool_calls))
            if self.verbose:
                out(
                    f"[模型决策] 调用 {len(msg.tool_calls)} 个工具",
                    "模型选择先执行工具再继续推理",
                )
            messages.append(msg.model_dump())

            if self.sequential:
                self.sequential.on_tool_decision(
                    round_num, [tc.function.name for tc in msg.tool_calls]
                )

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                self.activity.tool_call(fn_name, fn_args)

                result = run_tool_with_policy(
                    self.registry,
                    fn_name,
                    fn_args,
                    rate_key=rate_key,
                    confirm_handler=confirm_handler,
                    permission_tier=self.permission_tier,
                )
                if result.get("policy") == "rate_limit":
                    self.activity.log_event("rate_limit", tool=fn_name)

                # 压缩工具结果
                if self.enable_compression:
                    result_text = self._compressor.compress(fn_name, result)
                else:
                    result_text = ToolRegistry.result_text(result)

                self.activity.tool_result_event(
                    result.get("success", False), result_text
                )
                if self.sequential:
                    self.sequential.on_tool_result(
                        round_num, fn_name, bool(result.get("success", False))
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    }
                )
                last_tool = fn_name

        msg_text = "任务未完成，已达到最大迭代次数。"
        self.activity.error(msg_text)
        if self.verbose:
            warn(msg_text, f"已执行 {self.max_iterations} 轮")
        return msg_text, messages
