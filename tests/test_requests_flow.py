from pathlib import Path

import pytest

from transkript_bot.routers.chat_admin import create_chat_request
from transkript_bot.routers.media import create_user_request
from transkript_bot.storage.db import Storage, init_db


@pytest.mark.asyncio
async def test_auto_request_created_for_denied_user(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    storage = Storage(db_path)

    request_id, created = await create_user_request(storage, user_id=11)
    assert created is True
    pending = await storage.get_pending_request(kind="user", user_id=11, chat_id=None)
    assert pending is not None
    assert pending["status"] == "pending"
    assert pending["id"] == request_id


@pytest.mark.asyncio
async def test_chat_request_created(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    storage = Storage(db_path)

    request_id, created = await create_chat_request(storage, chat_id=77, requested_by_id=99)
    assert created is True
    pending = await storage.get_pending_request(kind="chat", user_id=None, chat_id=77)
    assert pending is not None
    assert pending["status"] == "pending"
    assert pending["id"] == request_id
