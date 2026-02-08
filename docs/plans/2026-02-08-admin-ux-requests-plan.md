# Admin UX + Requests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement role-aware commands and a DM-first admin UI with persistent user/chat access requests, approval/denial workflows, and clean inline menus.

**Architecture:** Add a `requests` table to SQLite with storage helpers, wire requests into media and chat admin flows, and build a menu/requests UI with inline keyboards and callback handlers. Set Telegram command scopes on startup to reflect roles.

**Tech Stack:** Python 3.13, aiogram v3, aiosqlite, uv/pytest.

---

### Task 1: Add requests table (schema + smoke test)

**Files:**
- Modify: `src/transkript_bot/storage/schema.sql`
- Test: `tests/test_storage_requests.py`

**Step 1: Write the failing test**

```python
import asyncio
from pathlib import Path

import pytest

from transkript_bot.storage.db import init_db, Storage


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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_storage_requests.py::test_requests_table_created -v`
Expected: FAIL with “no such table: requests” or missing method.

**Step 3: Write minimal implementation**

Add to `schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    user_id INTEGER,
    chat_id INTEGER,
    requested_by_id INTEGER,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_requests_kind_status ON requests(kind, status);
CREATE INDEX IF NOT EXISTS idx_requests_user_id ON requests(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_chat_id ON requests(chat_id);
```

Also add a minimal `create_request` method in `Storage` (see Task 2 for full API).

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_storage_requests.py::test_requests_table_created -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/transkript_bot/storage/schema.sql tests/test_storage_requests.py src/transkript_bot/storage/db.py
git commit -m "Add requests table"
```

---

### Task 2: Full storage API for requests + tests

**Files:**
- Modify: `src/transkript_bot/storage/db.py`
- Test: `tests/test_storage_requests.py`

**Step 1: Write failing tests**

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_storage_requests.py::test_request_dedup_and_list -v`
Expected: FAIL (methods missing / behavior wrong).

**Step 3: Implement minimal storage API**

Add methods to `Storage`:
- `get_request(id)`
- `get_pending_request(kind, user_id/chat_id)`
- `create_request(kind, user_id, chat_id, requested_by_id)` with dedup on pending
- `list_requests(kind, status, limit, offset)`
- `set_request_status(id, status, reason)`

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_storage_requests.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/transkript_bot/storage/db.py tests/test_storage_requests.py
git commit -m "Add request storage API"
```

---

### Task 3: Role-aware /help and /menu skeleton

**Files:**
- Modify: `src/transkript_bot/routers/common.py`
- Create: `src/transkript_bot/services/menu.py`
- Modify: `src/transkript_bot/services/keyboard.py`
- Test: `tests/test_menu.py`

**Step 1: Write failing tests**

```python
from transkript_bot.services.menu import build_help_text, MenuRole


def test_help_text_for_user():
    text = build_help_text(role=MenuRole.USER, in_private=True)
    assert "/admin" not in text
    assert "/menu" in text


def test_help_text_for_root_admin():
    text = build_help_text(role=MenuRole.ROOT_ADMIN, in_private=True)
    assert "/admin" in text
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_menu.py::test_help_text_for_user -v`
Expected: FAIL (module missing).

**Step 3: Implement minimal menu helpers**

- `MenuRole` enum with USER/CHAT_ADMIN/ROOT_ADMIN.
- `build_help_text(role, in_private)` returns a string list.
- Add `/menu` handler that shows an inline keyboard built by `build_menu_keyboard(role, in_private)` (can be minimal in this task).

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_menu.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/transkript_bot/routers/common.py src/transkript_bot/services/menu.py src/transkript_bot/services/keyboard.py tests/test_menu.py
git commit -m "Add role-aware help/menu helpers"
```

---

### Task 4: Request creation flows (user + chat)

**Files:**
- Modify: `src/transkript_bot/routers/media.py`
- Modify: `src/transkript_bot/routers/chat_admin.py`
- Modify: `src/transkript_bot/services/keyboard.py`
- Test: `tests/test_requests_flow.py`

**Step 1: Write failing tests**

```python
@pytest.mark.asyncio
async def test_auto_request_created_for_denied_user(tmp_path: Path):
    # Arrange: storage with user not allowed
    # Act: simulate denied media handling (call a helper function)
    # Assert: storage has pending request for the user
    assert pending_request["status"] == "pending"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_requests_flow.py::test_auto_request_created_for_denied_user -v`
Expected: FAIL.

**Step 3: Implement minimal code**

- In `media.handle_media`, when access denied in private: create pending user request (dedup) and respond with a “Request access” button.
- In `chat_admin`, add a callback from `/menu` for “Request chat access” that creates a pending chat request.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_requests_flow.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/transkript_bot/routers/media.py src/transkript_bot/routers/chat_admin.py src/transkript_bot/services/keyboard.py tests/test_requests_flow.py
git commit -m "Add request creation flows"
```

---

### Task 5: Root-admin requests UI (list + approve/deny)

**Files:**
- Modify: `src/transkript_bot/routers/admin.py`
- Modify: `src/transkript_bot/services/keyboard.py`
- Test: `tests/test_admin_requests.py`

**Step 1: Write failing tests**

```python
@pytest.mark.asyncio
async def test_approve_user_request_updates_user_flags(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    storage = Storage(db_path)
    req_id = await storage.create_request(kind="user", user_id=5, chat_id=None, requested_by_id=5)

    await storage.set_user_blocked(5, True)
    # Call handler helper to approve
    await approve_user_request(storage, req_id)

    user = await storage.get_user(5)
    assert user["is_allowed"] is True
    assert user["is_blocked"] is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_admin_requests.py::test_approve_user_request_updates_user_flags -v`
Expected: FAIL.

**Step 3: Implement minimal code**

- Add admin callbacks: `requests:list`, `requests:approve`, `requests:deny`.
- On approve user: `set_user_allowed(True)`, `set_user_blocked(False)` and update request status.
- On approve chat: `set_chat_enabled(True)`, `set_chat_allowed_senders('whitelist')`, update status.
- Use inline keyboards with compact rows and “Back” navigation.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_admin_requests.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/transkript_bot/routers/admin.py src/transkript_bot/services/keyboard.py tests/test_admin_requests.py
git commit -m "Add requests admin UI"
```

---

### Task 6: Telegram command scopes on startup

**Files:**
- Modify: `src/transkript_bot/bot.py`
- Create/Modify: `tests/test_bot_commands.py`

**Step 1: Write failing test**

```python
from transkript_bot.services.commands import build_command_scopes


def test_command_scopes_include_admins():
    scopes = build_command_scopes(root_admin_ids={1})
    assert "all_private_chats" in scopes
    assert "all_chat_administrators" in scopes
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bot_commands.py::test_command_scopes_include_admins -v`
Expected: FAIL.

**Step 3: Implement minimal code**

- Add `services/commands.py` helpers to build `BotCommand` lists and apply via `bot.set_my_commands` on startup.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_bot_commands.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/transkript_bot/bot.py src/transkript_bot/services/commands.py tests/test_bot_commands.py
git commit -m "Set command scopes on startup"
```

---

### Task 7: Full test run

**Step 1: Run all tests**

Run: `uv run pytest -v`
Expected: PASS.

**Step 2: Commit any fixes**

```bash
git add -A
git commit -m "Fix tests for admin UX"
```

---

## Notes
- Prefer DM for admin responses; group receives short confirmation only.
- Keep inline keyboards compact (1 button per row).
- Dedup requests: if a pending request exists, return its id and skip creation.

