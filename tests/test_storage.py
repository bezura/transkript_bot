import pytest
from transkript_bot.storage.db import init_db, Storage


@pytest.mark.asyncio
async def test_user_allowlist(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(str(db_path))
    store = Storage(str(db_path))
    await store.set_user_allowed(123, True)
    u = await store.get_user(123)
    assert u["is_allowed"] is True
