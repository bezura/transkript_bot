from __future__ import annotations

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
