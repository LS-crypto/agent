"""Skills 工具：列出与按需加载用户可调用的技能。"""

from __future__ import annotations

from core.skills.loader import discover_skills, read_skill_body
from core.tools.registry import ToolRegistry


class SkillsTools:
    def list_skills(self) -> dict:
        skills = discover_skills()
        return {
            "success": True,
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "path": str(s.path),
                }
                for s in skills
            ],
            "count": len(skills),
            "hint": "调用 use_skill(skill_name) 加载完整技能说明到上下文",
        }

    def use_skill(self, skill_name: str) -> dict:
        for s in discover_skills():
            if s.name == skill_name:
                body = read_skill_body(s.path)
                return {
                    "success": True,
                    "name": s.name,
                    "description": s.description,
                    "content": body[:12000],
                }
        names = [s.name for s in discover_skills()]
        return {
            "success": False,
            "error": f"未找到技能: {skill_name}",
            "available": names[:20],
        }


def register_skills_tools(registry: ToolRegistry) -> None:
    tools = SkillsTools()
    registry.register(
        "list_skills",
        "列出工作区与内置可供 Agent 使用的 Skills（技能说明书）。",
        {"type": "object", "properties": {}},
        lambda **_: tools.list_skills(),
    )
    registry.register(
        "use_skill",
        "加载指定 Skill 的完整 Markdown 说明，用于指导当前任务（如磁盘分析、安全命令、代码审查）。",
        {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "技能名，先用 list_skills 查看",
                },
            },
            "required": ["skill_name"],
        },
        lambda skill_name, **_: tools.use_skill(skill_name),
    )
