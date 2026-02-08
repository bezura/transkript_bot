from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite


async def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("schema.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(schema_sql)
        await db.commit()


class Storage:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def set_user_allowed(self, tg_id: int, allowed: bool) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (tg_id, is_allowed)
                VALUES (?, ?)
                ON CONFLICT(tg_id) DO UPDATE SET is_allowed = excluded.is_allowed
                """,
                (tg_id, int(allowed)),
            )
            await db.commit()

    async def set_user_blocked(self, tg_id: int, blocked: bool) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (tg_id, is_blocked)
                VALUES (?, ?)
                ON CONFLICT(tg_id) DO UPDATE SET is_blocked = excluded.is_blocked
                """,
                (tg_id, int(blocked)),
            )
            await db.commit()

    async def get_user(self, tg_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT tg_id, is_allowed, is_blocked, note, created_at FROM users WHERE tg_id = ?",
                (tg_id,),
            ) as cursor:
                row = await cursor.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["is_allowed"] = bool(data.get("is_allowed"))
            data["is_blocked"] = bool(data.get("is_blocked"))
            return data

    async def upsert_chat(self, chat_id: int, title: str | None, type_: str | None) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO chats (chat_id, title, type, enabled, allowed_senders, allowed_user_ids, require_reply, language)
                VALUES (?, ?, ?, 0, 'whitelist', ?, 0, 'auto')
                ON CONFLICT(chat_id) DO UPDATE SET title = excluded.title, type = excluded.type
                """,
                (chat_id, title, type_, json.dumps([])),
            )
            await db.commit()

    async def get_chat(self, chat_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT chat_id, title, type, enabled, allowed_senders, allowed_user_ids, require_reply, language
                FROM chats WHERE chat_id = ?
                """,
                (chat_id,),
            ) as cursor:
                row = await cursor.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["enabled"] = bool(data.get("enabled"))
            data["require_reply"] = bool(data.get("require_reply"))
            raw = data.get("allowed_user_ids")
            try:
                data["allowed_user_ids"] = json.loads(raw) if raw else []
            except json.JSONDecodeError:
                data["allowed_user_ids"] = []
            return data

    async def set_chat_enabled(self, chat_id: int, enabled: bool) -> None:
        await self._update_chat(chat_id, enabled=int(enabled))

    async def set_chat_allowed_senders(self, chat_id: int, allowed_senders: str) -> None:
        await self._update_chat(chat_id, allowed_senders=allowed_senders)

    async def set_chat_require_reply(self, chat_id: int, require_reply: bool) -> None:
        await self._update_chat(chat_id, require_reply=int(require_reply))

    async def _update_chat(self, chat_id: int, **fields: Any) -> None:
        if not fields:
            return
        columns = []
        values: list[Any] = []
        for key, value in fields.items():
            columns.append(f"{key} = ?")
            values.append(value)
        values.append(chat_id)
        sql = f"UPDATE chats SET {', '.join(columns)} WHERE chat_id = ?"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, values)
            await db.commit()

    async def create_request(
        self,
        *,
        kind: str,
        user_id: int | None,
        chat_id: int | None,
        requested_by_id: int,
    ) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO requests (kind, status, user_id, chat_id, requested_by_id)
                VALUES (?, 'pending', ?, ?, ?)
                """,
                (kind, user_id, chat_id, requested_by_id),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def create_job(
        self,
        *,
        chat_id: int,
        user_id: int,
        status: str,
        message_id: int | None = None,
        thread_id: int | None = None,
        file_id: str | None = None,
        file_name: str | None = None,
        status_message_id: int | None = None,
        progress_message_id: int | None = None,
        backend: str | None = None,
        duration_sec: float | None = None,
    ) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO jobs (
                    chat_id, user_id, message_id, thread_id, file_id, file_name,
                    duration_sec, backend, status, status_message_id, progress_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    user_id,
                    message_id,
                    thread_id,
                    file_id,
                    file_name,
                    duration_sec,
                    backend,
                    status,
                    status_message_id,
                    progress_message_id,
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def update_job(self, job_id: int, **fields: Any) -> None:
        if not fields:
            return
        columns = []
        values: list[Any] = []
        for key, value in fields.items():
            columns.append(f"{key} = ?")
            values.append(value)
        values.append(job_id)
        sql = f"UPDATE jobs SET {', '.join(columns)} WHERE id = ?"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, values)
            await db.commit()

    async def get_recent_durations(self, limit: int = 10) -> list[int]:
        durations: list[int] = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT started_at, finished_at FROM jobs
                WHERE status = 'done' AND started_at IS NOT NULL AND finished_at IS NOT NULL
                ORDER BY finished_at DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
        for row in rows:
            try:
                start = float(row["started_at"])
                end = float(row["finished_at"])
            except (TypeError, ValueError):
                continue
            durations.append(int(end - start))
        return durations

    async def get_stats(self) -> dict[str, int]:
        async with aiosqlite.connect(self.db_path) as db:
            users_total = await self._fetch_count(db, "SELECT COUNT(*) FROM users")
            users_allowed = await self._fetch_count(
                db, "SELECT COUNT(*) FROM users WHERE is_allowed = 1"
            )
            users_blocked = await self._fetch_count(
                db, "SELECT COUNT(*) FROM users WHERE is_blocked = 1"
            )
            chats_total = await self._fetch_count(db, "SELECT COUNT(*) FROM chats")
            jobs_total = await self._fetch_count(db, "SELECT COUNT(*) FROM jobs")
        return {
            "users_total": users_total,
            "users_allowed": users_allowed,
            "users_blocked": users_blocked,
            "chats_total": chats_total,
            "jobs_total": jobs_total,
        }

    @staticmethod
    async def _fetch_count(db: aiosqlite.Connection, sql: str) -> int:
        async with db.execute(sql) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row else 0
