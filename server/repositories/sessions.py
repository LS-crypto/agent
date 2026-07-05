"""会话 CRUD（每用户独立 SQLite）。"""



from __future__ import annotations



import json

import uuid

from datetime import datetime

from typing import Any



from core.agent.prompts import CODING_AGENT_SYSTEM

from core.agent.permissions import normalize_tier

from core.models.catalog import AUTO_MODEL_ID, resolve_model_choice

from server.db.user_database import get_user_connection

from server.services.user_provision import provision_user_storage





def _now() -> str:

    return datetime.now().isoformat(timespec="seconds")





def _default_messages() -> list[dict[str, Any]]:

    return [{"role": "system", "content": CODING_AGENT_SYSTEM}]





def _normalize_model(model: str | None) -> str:

    mid = model or AUTO_MODEL_ID

    if mid == AUTO_MODEL_ID:

        return AUTO_MODEL_ID

    resolve_model_choice(mid)

    return mid





def _normalize_permission(permission: str | None) -> str:

    return normalize_tier(permission)





def _ensure_user_db(user_id: str) -> None:

    provision_user_storage(user_id)





class SessionRepository:

    def create(

        self,

        user_id: str,

        title: str = "新会话",

        *,

        model: str = AUTO_MODEL_ID,

        permission: str = "balanced",

    ) -> dict[str, Any]:

        _ensure_user_db(user_id)

        session_id = str(uuid.uuid4())

        now = _now()

        messages = _default_messages()

        model = _normalize_model(model)

        permission = _normalize_permission(permission)

        with get_user_connection(user_id) as conn:

            conn.execute(

                """

                INSERT INTO sessions (

                    id, user_id, title, messages_json, model, permission_level,

                    created_at, updated_at

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)

                """,

                (

                    session_id,

                    user_id,

                    title,

                    json.dumps(messages, ensure_ascii=False),

                    model,

                    permission,

                    now,

                    now,

                ),

            )

        return self.get(session_id, user_id)



    def list_by_user(self, user_id: str) -> list[dict[str, Any]]:

        _ensure_user_db(user_id)

        with get_user_connection(user_id) as conn:

            rows = conn.execute(

                """

                SELECT id, user_id, title, model, permission_level, created_at, updated_at

                FROM sessions

                ORDER BY updated_at DESC

                """,

            ).fetchall()

        return [self._row_summary(dict(row)) for row in rows]



    @staticmethod

    def _row_summary(row: dict[str, Any]) -> dict[str, Any]:

        if "permission_level" in row:

            row["permission"] = row.pop("permission_level")

        row.setdefault("permission", "balanced")

        return row



    def get(self, session_id: str, user_id: str) -> dict[str, Any]:

        _ensure_user_db(user_id)

        with get_user_connection(user_id) as conn:

            row = conn.execute(

                """

                SELECT id, user_id, title, messages_json, model, permission_level,

                       created_at, updated_at

                FROM sessions

                WHERE id = ? AND user_id = ?

                """,

                (session_id, user_id),

            ).fetchone()

        if row is None:

            raise KeyError(f"会话不存在: {session_id}")

        data = dict(row)

        data["messages"] = json.loads(data.pop("messages_json"))

        data.setdefault("model", AUTO_MODEL_ID)

        data["permission"] = data.pop("permission_level", "balanced")

        return data



    def append_user_message(
        self,
        session_id: str,
        user_id: str,
        content: str,
        *,
        title: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """立即写入用户消息，避免长任务进行中刷新丢会话。"""
        session = self.get(session_id, user_id)
        messages = list(session["messages"])
        messages.append({"role": "user", "content": content})
        kwargs: dict[str, Any] = {}
        if title is not None:
            kwargs["title"] = title
        if model is not None:
            kwargs["model"] = model
        return self.update_messages(session_id, user_id, messages, **kwargs)

    def update_messages(

        self,

        session_id: str,

        user_id: str,

        messages: list[dict[str, Any]],

        *,

        title: str | None = None,

        model: str | None = None,

    ) -> dict[str, Any]:

        now = _now()

        with get_user_connection(user_id) as conn:

            if title is not None and model is not None:

                conn.execute(

                    """

                    UPDATE sessions

                    SET messages_json = ?, title = ?, model = ?, updated_at = ?

                    WHERE id = ? AND user_id = ?

                    """,

                    (

                        json.dumps(messages, ensure_ascii=False),

                        title,

                        _normalize_model(model),

                        now,

                        session_id,

                        user_id,

                    ),

                )

            elif title is not None:

                conn.execute(

                    """

                    UPDATE sessions

                    SET messages_json = ?, title = ?, updated_at = ?

                    WHERE id = ? AND user_id = ?

                    """,

                    (

                        json.dumps(messages, ensure_ascii=False),

                        title,

                        now,

                        session_id,

                        user_id,

                    ),

                )

            elif model is not None:

                conn.execute(

                    """

                    UPDATE sessions

                    SET messages_json = ?, model = ?, updated_at = ?

                    WHERE id = ? AND user_id = ?

                    """,

                    (

                        json.dumps(messages, ensure_ascii=False),

                        _normalize_model(model),

                        now,

                        session_id,

                        user_id,

                    ),

                )

            else:

                conn.execute(

                    """

                    UPDATE sessions

                    SET messages_json = ?, updated_at = ?

                    WHERE id = ? AND user_id = ?

                    """,

                    (

                        json.dumps(messages, ensure_ascii=False),

                        now,

                        session_id,

                        user_id,

                    ),

                )

            if conn.total_changes == 0:

                raise KeyError(f"会话不存在: {session_id}")

        return self.get(session_id, user_id)



    def set_model(self, session_id: str, user_id: str, model: str) -> dict[str, Any]:

        now = _now()

        model = _normalize_model(model)

        with get_user_connection(user_id) as conn:

            conn.execute(

                """

                UPDATE sessions SET model = ?, updated_at = ?

                WHERE id = ? AND user_id = ?

                """,

                (model, now, session_id, user_id),

            )

            if conn.total_changes == 0:

                raise KeyError(f"会话不存在: {session_id}")

        return self.get(session_id, user_id)



    def set_permission(

        self, session_id: str, user_id: str, permission: str

    ) -> dict[str, Any]:

        now = _now()

        permission = _normalize_permission(permission)

        with get_user_connection(user_id) as conn:

            conn.execute(

                """

                UPDATE sessions SET permission_level = ?, updated_at = ?

                WHERE id = ? AND user_id = ?

                """,

                (permission, now, session_id, user_id),

            )

            if conn.total_changes == 0:

                raise KeyError(f"会话不存在: {session_id}")

        return self.get(session_id, user_id)



    def reset(self, session_id: str, user_id: str) -> dict[str, Any]:

        return self.update_messages(session_id, user_id, _default_messages())



    def delete(self, session_id: str, user_id: str) -> None:

        with get_user_connection(user_id) as conn:

            conn.execute(

                "DELETE FROM sessions WHERE id = ? AND user_id = ?",

                (session_id, user_id),

            )

            if conn.total_changes == 0:

                raise KeyError(f"会话不存在: {session_id}")



    def rename(self, session_id: str, user_id: str, title: str) -> dict[str, Any]:

        now = _now()

        with get_user_connection(user_id) as conn:

            conn.execute(

                """

                UPDATE sessions SET title = ?, updated_at = ?

                WHERE id = ? AND user_id = ?

                """,

                (title, now, session_id, user_id),

            )

            if conn.total_changes == 0:

                raise KeyError(f"会话不存在: {session_id}")

        return self.get(session_id, user_id)



    def count_for_user(self, user_id: str) -> int:

        _ensure_user_db(user_id)

        with get_user_connection(user_id) as conn:

            row = conn.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()

        return int(row["c"]) if row else 0


