"""会话消息即时持久化。"""

from __future__ import annotations

from server.repositories.sessions import SessionRepository


def test_append_user_message_persists_immediately() -> None:
    repo = SessionRepository()
    user_id = "persist-test-user"
    session = repo.create(user_id, title="新会话", model="qwen3.6-flash")
    session_id = session["id"]

    updated = repo.append_user_message(
        session_id,
        user_id,
        "帮我写一个小项目",
        title="帮我写一个小项目",
        model="qwen3.6-flash",
    )

    assert updated["title"] == "帮我写一个小项目"
    messages = updated["messages"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "帮我写一个小项目"

    reloaded = repo.get(session_id, user_id)
    assert reloaded["messages"][-1]["content"] == "帮我写一个小项目"

    repo.delete(session_id, user_id)
