"""编程助手 Agent：Loop + 工具 + 记忆 + 活动记录。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.agent.activity import ActivityLogger
from core.agent.loop import AgentLoop
from core.agent.memory import Session
from core.agent.prompts import CODING_AGENT_SYSTEM
from core.agent.vector_memory import VectorMemory
from core.agent.permissions import (
    PermissionTier,
    get_default_tier,
    normalize_tier,
    set_permission_tier,
)
from core.config import MODEL_CODER
from core.agent.sequential import SequentialTracker, model_supports_sequential
from core.models.catalog import AUTO_MODEL_ID, resolve_model_choice
from core.models.profiles import get_model_profile
from core.skills.loader import build_skills_prompt
from core.tools.build import build_coding_registry
from core.user.paths import ensure_user_dirs, workspace_projects


class CodingAgent:
    def __init__(
        self,
        user_id: str = "default",
        *,
        resume: bool = True,
        verbose: bool = False,
        persist_json: bool = True,
        messages: list[dict[str, Any]] | None = None,
        api_key: str | None = None,
    ) -> None:
        self.user_id = user_id
        self.verbose = verbose
        ensure_user_dirs(user_id)
        skills_block = build_skills_prompt(["karpathy-guidelines", "design-taste-frontend"])
        system = CODING_AGENT_SYSTEM
        if skills_block:
            system = f"{CODING_AGENT_SYSTEM}\n\n{skills_block}"
        self.session = Session(
            user_id,
            system,
            persist_json=persist_json,
            messages=messages,
        )
        if resume and persist_json:
            self.session.load()
        self.registry = build_coding_registry(user_id)
        self.memory = VectorMemory(user_id)
        self.activity = ActivityLogger(user_id, mirror_console=verbose)
        self.loop = AgentLoop(
            self.registry,
            user_id=user_id,
            model=MODEL_CODER,
            system_prompt=system,
            activity=self.activity,
            verbose=verbose,
            enable_routing=True,
            enable_compression=True,
            client=create_client(api_key) if api_key else None,
        )
        self._session_active = False

    def _apply_model_profile(self, model_id: str | None, *, routing: bool) -> None:
        """按所选模型注入特色 prompt、技能与 Loop 参数。"""
        mid = model_id if (model_id and not routing) else AUTO_MODEL_ID
        profile = get_model_profile(mid)

        base_skills = ["karpathy-guidelines", "design-taste-frontend"]
        skill_names = list(dict.fromkeys([*base_skills, *profile.skills]))
        skills_block = build_skills_prompt(skill_names)

        mode_block = (
            f"\n\n## 当前模型模式：{profile.tagline}\n"
            f"{profile.extra_prompt}"
        )
        if profile.prefer_tools:
            mode_block += f"\n优先使用工具：{', '.join(profile.prefer_tools)}。"

        system = CODING_AGENT_SYSTEM
        if skills_block:
            system = f"{system}\n\n{skills_block}"
        system = f"{system}{mode_block}"

        self.loop.system_prompt = system
        self.loop.max_iterations = profile.max_iterations
        self.loop.temperature = profile.temperature
        self.loop.enable_compression = profile.enable_compression
        if profile.max_read_chars:
            self.loop._compressor.set_tool_limit("read_file", profile.max_read_chars)

        if self.session.messages and self.session.messages[0].get("role") == "system":
            self.session.messages[0]["content"] = system

    @property
    def workspace(self) -> str:
        return str(workspace_projects(self.user_id))

    def start_session(self) -> None:
        if not self._session_active:
            self.activity.session_start()
            self._session_active = True

    def chat(
        self,
        user_input: str,
        *,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        confirm_handler: Callable[[str, dict[str, Any]], bool] | None = None,
        session_id: str | None = None,
        model: str | None = None,
        enable_routing: bool | None = None,
        permission: str | None = None,
    ) -> str:
        self.start_session()
        if on_event is not None:
            self.activity.on_event = on_event

        tier: PermissionTier = (
            normalize_tier(permission) if permission else get_default_tier()
        )
        set_permission_tier(tier)
        self.loop.permission_tier = tier

        fixed_model, route = resolve_model_choice(model) if model else (None, True)
        if enable_routing is not None:
            route = enable_routing
        if fixed_model:
            self.loop.model = fixed_model
        elif not route:
            self.loop.model = MODEL_CODER
        self.loop.enable_routing = route

        self._apply_model_profile(fixed_model or model, routing=route)

        seq_enabled = model_supports_sequential(fixed_model or model or "")
        if route and not fixed_model:
            seq_enabled = True
        self.loop.sequential = SequentialTracker(
            enabled=seq_enabled,
            emit=on_event,
        )

        mem_ctx = self.memory.format_context(user_input)
        enriched = user_input
        if mem_ctx:
            enriched = f"{mem_ctx}\n\n## 用户请求\n{user_input}"
        final, self.session.messages = self.loop.run(
            enriched,
            self.session.messages,
            confirm_handler=confirm_handler,
            session_id=session_id,
        )
        self.session.save()
        if final and len(final) > 20:
            self.memory.add(f"Q: {user_input[:200]} A: {final[:400]}")
        return final

    def reset(self) -> None:
        self.session.reset()
        self.session.save()
        if self._session_active:
            self.activity.session_end()
            self._session_active = False

    def end_session(self) -> None:
        if self._session_active:
            self.activity.session_end()
            self._session_active = False
