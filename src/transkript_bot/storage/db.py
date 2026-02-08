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
