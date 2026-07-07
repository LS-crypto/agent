"""Skills 加载测试。"""

from core.skills.loader import discover_skills, list_skill_names


def test_discover_workspace_skills():
    names = list_skill_names()
    assert "karpathy-guidelines" in names
    assert "disk-storage" in names
    assert len(discover_skills()) >= 5
