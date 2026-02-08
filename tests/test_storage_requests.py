from pathlib import Path

import pytest

from transkript_bot.storage.db import Storage, init_db


@pytest.mark.asyncio
async def test_requests_table_created(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    storage = Storage(db_path)

    # This will fail until the table exists.
    await storage.create_request(
        kind="user",
        user_id=123,
        chat_id=None,
        requested_by_id=123,
    )
