"""Skills 加载层：扫描工作区 taste-skill / karpathy 技能元数据。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillMeta:
    name: str
    description: str
    path: Path


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end < 0:
        return {}
    block = text[3:end].strip()
    meta: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()
    return meta


from core.paths import WORKSPACE_ROOT


def _workspace_root() -> Path:
    return WORKSPACE_ROOT


def read_skill_body(path: Path) -> str:
    """读取 SKILL.md 正文（去掉 YAML frontmatter）。"""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end >= 0:
            return text[end + 3 :].strip()
    return text.strip()


def discover_skills() -> list[SkillMeta]:
    root = _workspace_root()
    scan_dirs = [
        Path(__file__).resolve().parent / "custom",
        root / "taste-skill" / ".agents" / "skills",
        root / "andrej-karpathy-skills" / "skills",
    ]
    found: list[SkillMeta] = []
    seen: set[str] = set()
    for base in scan_dirs:
        if not base.is_dir():
            continue
        for path in base.rglob("SKILL.md"):
            text = path.read_text(encoding="utf-8")
            meta = _parse_frontmatter(text)
            name = meta.get("name") or path.parent.name
            if name in seen:
                continue
            seen.add(name)
            found.append(
                SkillMeta(
                    name=name,
                    description=meta.get("description", ""),
                    path=path,
                )
            )
    return found


def build_skills_prompt(active: list[str] | None = None) -> str:
    skills = discover_skills()
    if active:
        active_set = set(active)
        skills = [s for s in skills if s.name in active_set]
    if not skills:
        return ""
    lines = ["## 已加载 Skills", ""]
    for s in skills[:8]:
        desc = s.description[:200] if s.description else ""
        lines.append(f"- **{s.name}**: {desc}")
    lines.append("")
    lines.append("编写代码或 UI 时遵循上述技能描述。")
    return "\n".join(lines)


def list_skill_names() -> list[str]:
    return [s.name for s in discover_skills()]
