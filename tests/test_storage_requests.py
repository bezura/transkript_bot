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


@pytest.mark.asyncio
async def test_request_dedup_and_list(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    storage = Storage(db_path)

    first = await storage.create_request(kind="user", user_id=1, chat_id=None, requested_by_id=1)
    second = await storage.create_request(kind="user", user_id=1, chat_id=None, requested_by_id=1)

    assert first == second
    pending = await storage.list_requests(kind="user", status="pending", limit=10, offset=0)
    assert len(pending) == 1
    assert pending[0]["user_id"] == 1


@pytest.mark.asyncio
async def test_request_status_update(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    storage = Storage(db_path)

    req_id = await storage.create_request(kind="chat", user_id=None, chat_id=42, requested_by_id=100)
    await storage.set_request_status(req_id, status="approved", reason="ok")

    updated = await storage.get_request(req_id)
    assert updated["status"] == "approved"
    assert updated["reason"] == "ok"
