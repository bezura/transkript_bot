import pytest
from transkript_bot.storage.db import init_db, Storage


@pytest.mark.asyncio
async def test_chat_upsert_and_get(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(str(db_path))
    store = Storage(str(db_path))
    await store.upsert_chat(chat_id=1, title="Test", type_="group")
    chat = await store.get_chat(1)
    assert chat["enabled"] is False
    assert chat["allowed_senders"] == "whitelist"


@pytest.mark.asyncio
async def test_chat_settings_updates(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(str(db_path))
    store = Storage(str(db_path))
    await store.upsert_chat(chat_id=1, title="Test", type_="group")
    await store.set_chat_enabled(1, True)
    await store.set_chat_allowed_senders(1, "all")
    await store.set_chat_require_reply(1, True)
    chat = await store.get_chat(1)
    assert chat["enabled"] is True
    assert chat["allowed_senders"] == "all"
    assert chat["require_reply"] is True
