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


@pytest.mark.asyncio
async def test_user_blocked(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(str(db_path))
    store = Storage(str(db_path))
    await store.set_user_blocked(321, True)
    u = await store.get_user(321)
    assert u["is_blocked"] is True


@pytest.mark.asyncio
async def test_job_durations(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(str(db_path))
    store = Storage(str(db_path))
    job_id = await store.create_job(chat_id=1, user_id=2, status="queued")
    await store.update_job(job_id, status="done", started_at=10.0, finished_at=25.0)
    durations = await store.get_recent_durations(limit=5)
    assert durations[0] == 15
