from pathlib import Path

import pytest

from transkript_bot.routers.admin import approve_user_request
from transkript_bot.storage.db import Storage, init_db


@pytest.mark.asyncio
async def test_approve_user_request_updates_user_flags(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    storage = Storage(db_path)
    req_id = await storage.create_request(kind="user", user_id=5, chat_id=None, requested_by_id=5)

    await storage.set_user_blocked(5, True)
    await approve_user_request(storage, req_id)

    user = await storage.get_user(5)
    assert user["is_allowed"] is True
    assert user["is_blocked"] is False

    request = await storage.get_request(req_id)
    assert request["status"] == "approved"
