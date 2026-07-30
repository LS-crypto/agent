"""会话消息即时持久化 + 软删除/恢复。"""

from __future__ import annotations

import pytest

from server.repositories.sessions import SessionRepository


def test_append_user_message_persists_immediately() -> None:
    repo = SessionRepository()
    user_id = "persist-test-user"
    session = repo.create(user_id, title="新会话", model="deepseek-chat")
    session_id = session["id"]

    updated = repo.append_user_message(
        session_id,
        user_id,
        "帮我写一个小项目",
        title="帮我写一个小项目",
        model="deepseek-chat",
    )

    assert updated["title"] == "帮我写一个小项目"
    messages = updated["messages"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "帮我写一个小项目"

    reloaded = repo.get(session_id, user_id)
    assert reloaded["messages"][-1]["content"] == "帮我写一个小项目"

    repo.delete(session_id, user_id)


# ---------- 软删除 / 恢复 / 彻底删除 ----------


def test_soft_delete_hides_from_list_but_keeps_in_db() -> None:
    """叉掉=软删除：list_by_user 不再返回，但 list_archived 返回。"""
    repo = SessionRepository()
    user_id = "soft-delete-user"
    session_id = repo.create(user_id, "测试会话")["id"]

    repo.delete(session_id, user_id)

    # 活跃列表看不到
    active = repo.list_by_user(user_id)
    assert all(s["id"] != session_id for s in active)

    # 归档列表能看到
    archived = repo.list_archived(user_id)
    archived_ids = [s["id"] for s in archived]
    assert session_id in archived_ids
    assert any(s.get("archived_at") for s in archived)


def test_soft_delete_idempotent_raises_on_second_call() -> None:
    """对已归档的会话重复 delete 应报错，避免误以为成功。"""
    repo = SessionRepository()
    user_id = "soft-delete-idem"
    session_id = repo.create(user_id, "测试")["id"]

    repo.delete(session_id, user_id)
    with pytest.raises(KeyError):
        repo.delete(session_id, user_id)


def test_restore_brings_session_back_to_active_list() -> None:
    """restore 把 archived_at 清空，重新出现在活跃列表。"""
    repo = SessionRepository()
    user_id = "restore-user"
    session_id = repo.create(user_id, "可恢复会话")["id"]

    repo.delete(session_id, user_id)
    assert all(s["id"] != session_id for s in repo.list_by_user(user_id))

    restored = repo.restore(session_id, user_id)
    assert restored["id"] == session_id

    active_ids = [s["id"] for s in repo.list_by_user(user_id)]
    assert session_id in active_ids
    assert all(s["id"] != session_id for s in repo.list_archived(user_id))


def test_restore_on_non_archived_raises() -> None:
    """对未归档的会话调用 restore 应报错。"""
    repo = SessionRepository()
    user_id = "restore-bad"
    session_id = repo.create(user_id, "未归档")["id"]

    with pytest.raises(KeyError):
        repo.restore(session_id, user_id)


def test_hard_delete_purges_session_completely() -> None:
    """hard_delete 真删：两个列表都不再返回，get 抛 KeyError。"""
    repo = SessionRepository()
    user_id = "hard-delete-user"
    session_id = repo.create(user_id, "要被彻底删除")["id"]

    repo.delete(session_id, user_id)  # 先归档
    repo.hard_delete(session_id, user_id)

    assert all(s["id"] != session_id for s in repo.list_by_user(user_id))
    assert all(s["id"] != session_id for s in repo.list_archived(user_id))
    with pytest.raises(KeyError):
        repo.get(session_id, user_id)


def test_soft_delete_does_not_affect_other_users() -> None:
    """多用户隔离：归档 A 的会话不影响 B 的列表。"""
    repo = SessionRepository()
    a_id = "isolation-user-a"
    b_id = "isolation-user-b"
    a_session = repo.create(a_id, "A 的会话")["id"]
    b_session = repo.create(b_id, "B 的会话")["id"]

    repo.delete(a_session, a_id)

    # B 的活跃列表不应该有 A 的归档会话
    assert all(s["id"] != a_session for s in repo.list_by_user(b_id))
    # B 的归档列表也不应该有
    assert all(s["id"] != a_session for s in repo.list_archived(b_id))
    # B 的会话还在
    assert any(s["id"] == b_session for s in repo.list_by_user(b_id))
