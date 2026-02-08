import pytest
from transkript_bot.storage.db import init_db, Storage


@pytest.mark.asyncio
async def test_stats_counts(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(str(db_path))
    store = Storage(str(db_path))
    await store.set_user_allowed(1, True)
    await store.set_user_blocked(2, True)
    await store.upsert_chat(chat_id=1, title="Test", type_="group")
    job_id = await store.create_job(chat_id=1, user_id=1, status="done")
    await store.update_job(job_id, started_at=1.0, finished_at=2.0)

    stats = await store.get_stats()
    assert stats["users_total"] == 2
    assert stats["users_allowed"] == 1
    assert stats["users_blocked"] == 1
    assert stats["chats_total"] == 1
    assert stats["jobs_total"] == 1
