# Telegram Transcription Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **Skill reference:** @superpowers:executing-plans

**Goal:** Implement a production-ready aiogram v3 bot that transcribes audio/video in private and group chats, enforces allowlist access, supports admin controls, provides queueing and progress updates, and runs in Colab with auto-shutdown.

**Architecture:** Single-process bot with an in-memory queue and worker, backed by SQLite for persistence. Hybrid transcription backend: WhisperX CLI on GPU, faster-whisper on CPU/MPS. Outputs TXT/MD/JSON with speaker labels.

**Tech Stack:** Python 3.13+, aiogram v3, aiosqlite, pydantic-settings, psutil, faster-whisper (optional), WhisperX CLI (optional), ffmpeg (system).

---

### Task 1: Project skeleton and configuration

**Files:**
- Modify: `pyproject.toml`
- Create: `src/transkript_bot/__init__.py`
- Create: `src/transkript_bot/main.py`
- Create: `src/transkript_bot/config.py`
- Create: `.env.example`
- Modify: `.gitignore`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
from transkript_bot.config import Settings

def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.default_language == "auto"
    assert s.idle_shutdown_minutes == 5
    assert s.allowed_senders_default == "whitelist"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing attributes.

**Step 3: Write minimal implementation**

```python
# src/transkript_bot/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    bot_token: str
    root_admin_ids: list[int] = []
    hf_token: str | None = None
    storage_path: str = "./data/bot.db"
    media_dir: str = "./data/media"
    idle_shutdown_minutes: int = 5
    default_language: str = "auto"
    allowed_senders_default: str = "whitelist"
    backend_force: str | None = None
    whisperx_cmd: str = "whisperx"

    class Config:
        env_file = ".env"
        case_sensitive = False
```

Update `pyproject.toml` dependencies to include:
- `aiogram>=3`
- `aiosqlite`
- `pydantic-settings`
- `psutil`
- `aiofiles`
- `faster-whisper` (optional for CPU/MPS)
- `pytest`, `pytest-asyncio` (dev)

Add minimal `main.py` with a `main()` placeholder and logging init.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/transkript_bot/config.py src/transkript_bot/main.py .env.example .gitignore tests/test_config.py
git commit -m "feat: add config and project skeleton"
```

---

### Task 2: SQLite schema and storage layer

**Files:**
- Create: `src/transkript_bot/storage/schema.sql`
- Create: `src/transkript_bot/storage/db.py`
- Test: `tests/test_storage.py`

**Step 1: Write the failing test**

```python
# tests/test_storage.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL due to missing module or functions.

**Step 3: Write minimal implementation**

- `schema.sql` with `users`, `chats`, `jobs` tables.
- `db.py` with `init_db()` and `Storage` class using `aiosqlite`.
  - Include `status_message_id` and `progress_message_id` in `jobs` so we can edit progress messages.
  - Include `thread_id` to respond in topics.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/storage/schema.sql src/transkript_bot/storage/db.py tests/test_storage.py
git commit -m "feat: add sqlite schema and storage layer"
```

---

### Task 3: Access control logic

**Files:**
- Create: `src/transkript_bot/services/access.py`
- Test: `tests/test_access.py`

**Step 1: Write the failing test**

```python
# tests/test_access.py
from transkript_bot.services.access import can_process


def test_allowlist_only():
    chat = {"enabled": True, "allowed_senders": "whitelist", "allowed_user_ids": []}
    assert can_process(user_allowed=True, is_chat_admin=False, chat=chat) is True
    assert can_process(user_allowed=False, is_chat_admin=False, chat=chat) is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_access.py -v`
Expected: FAIL (missing module/function).

**Step 3: Write minimal implementation**

```python
# src/transkript_bot/services/access.py

def can_process(*, user_allowed: bool, is_chat_admin: bool, chat: dict) -> bool:
    if not chat.get("enabled", False):
        return False
    if is_chat_admin:
        return True
    mode = chat.get("allowed_senders", "whitelist")
    if mode == "all":
        return True
    if mode == "whitelist":
        return user_allowed
    if mode == "list":
        return False
    return False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_access.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/services/access.py tests/test_access.py
git commit -m "feat: add access control logic"
```

---

### Task 4: Queue, ETA, and job persistence

**Files:**
- Create: `src/transkript_bot/services/queue.py`
- Modify: `src/transkript_bot/storage/db.py`
- Test: `tests/test_queue.py`

**Step 1: Write the failing test**

```python
# tests/test_queue.py
from transkript_bot.services.queue import estimate_eta


def test_eta_from_history():
    durations = [60, 120, 90]
    assert estimate_eta(durations, position=3) == 180
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_queue.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/transkript_bot/services/queue.py

def estimate_eta(durations: list[int], position: int) -> int:
    if position <= 1:
        return 0
    if not durations:
        return -1
    avg = sum(durations) // len(durations)
    return avg * (position - 1)
```

Extend `Storage` with job insert/update and query last durations (based on `finished_at - started_at`).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_queue.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/services/queue.py src/transkript_bot/storage/db.py tests/test_queue.py
git commit -m "feat: add queue ETA utilities and job persistence"
```

---

### Task 5: Transcript formatting

**Files:**
- Create: `src/transkript_bot/transcription/formatting.py`
- Test: `tests/test_formatting.py`

**Step 1: Write the failing test**

```python
# tests/test_formatting.py
from transkript_bot.transcription.formatting import segments_to_txt


def test_segments_to_txt():
    segments = [{"start": 0.0, "end": 1.23, "speaker": "SPEAKER_00", "text": "Привет"}]
    out = segments_to_txt(segments)
    assert "SPEAKER_00" in out
    assert "Привет" in out
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_formatting.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/transkript_bot/transcription/formatting.py

def sec_to_hms(sec: float) -> str:
    m = int(sec // 60)
    s = sec % 60
    return f"{m:02d}:{s:06.3f}"


def segments_to_txt(segments: list[dict]) -> str:
    lines = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = sec_to_hms(float(seg.get("start", 0.0)))
        end = sec_to_hms(float(seg.get("end", 0.0)))
        speaker = seg.get("speaker", "SPEAKER")
        lines.append(f"[{start} – {end}] {speaker}:")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_formatting.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/transcription/formatting.py tests/test_formatting.py
git commit -m "feat: add transcript formatting"
```

---

### Task 6: Backend detection and system info

**Files:**
- Create: `src/transkript_bot/services/system_info.py`
- Create: `src/transkript_bot/transcription/backend.py`
- Test: `tests/test_backend.py`

**Step 1: Write the failing test**

```python
# tests/test_backend.py
from transkript_bot.transcription.backend import choose_backend


def test_choose_backend_force():
    assert choose_backend(force="whisperx", has_gpu=False) == "whisperx"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_backend.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/transkript_bot/transcription/backend.py

def choose_backend(*, force: str | None, has_gpu: bool) -> str:
    if force:
        return force
    return "whisperx" if has_gpu else "faster"
```

`system_info.py` should gather OS, Python, CPU/RAM, disk, and NVIDIA GPU info (if `nvidia-smi` exists). Provide a dict for admin output and a short string for startup notification.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_backend.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/services/system_info.py src/transkript_bot/transcription/backend.py tests/test_backend.py
git commit -m "feat: add backend selection and system info"
```

---

### Task 7: WhisperX CLI runner

**Files:**
- Create: `src/transkript_bot/transcription/whisperx_cli.py`
- Test: `tests/test_whisperx_cli.py`

**Step 1: Write the failing test**

```python
# tests/test_whisperx_cli.py
from transkript_bot.transcription.whisperx_cli import build_whisperx_cmd


def test_build_cmd():
    cmd = build_whisperx_cmd("in.wav", "out", "large-v2", "auto", False, None)
    assert "whisperx" in cmd[0]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_whisperx_cli.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement `build_whisperx_cmd()` and `run_whisperx()` that runs subprocess, parses JSON output, and returns segments list.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_whisperx_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/transcription/whisperx_cli.py tests/test_whisperx_cli.py
git commit -m "feat: add WhisperX CLI runner"
```

---

### Task 8: faster-whisper runner (CPU/MPS)

**Files:**
- Create: `src/transkript_bot/transcription/faster_whisper.py`
- Test: `tests/test_faster_whisper.py`

**Step 1: Write the failing test**

```python
# tests/test_faster_whisper.py
from transkript_bot.transcription.faster_whisper import normalize_segments


def test_normalize_segments():
    segs = [{"start": 0.0, "end": 1.0, "text": "ok"}]
    out = normalize_segments(segs)
    assert out[0]["speaker"] == "SPEAKER_00"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_faster_whisper.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement `run_faster_whisper()` with `faster_whisper.WhisperModel`, returning segments with `speaker` set to `SPEAKER_00`. If diarization requested but not available, log warning and continue without diarization.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_faster_whisper.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/transcription/faster_whisper.py tests/test_faster_whisper.py
git commit -m "feat: add faster-whisper runner"
```

---

### Task 9: Media handling and FFmpeg conversion

**Files:**
- Create: `src/transkript_bot/transcription/media.py`
- Test: `tests/test_media.py`

**Step 1: Write the failing test**

```python
# tests/test_media.py
from transkript_bot.transcription.media import build_ffmpeg_cmd


def test_build_ffmpeg_cmd():
    cmd = build_ffmpeg_cmd("in.mp4", "out.wav")
    assert cmd[:2] == ["ffmpeg", "-y"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_media.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement `build_ffmpeg_cmd()` and `convert_to_wav()` (mono, 16kHz).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_media.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/transcription/media.py tests/test_media.py
git commit -m "feat: add ffmpeg media conversion"
```

---

### Task 10: Bot routers and commands

**Files:**
- Create: `src/transkript_bot/bot.py`
- Create: `src/transkript_bot/routers/common.py`
- Create: `src/transkript_bot/routers/admin.py`
- Create: `src/transkript_bot/routers/chat_admin.py`
- Create: `src/transkript_bot/routers/media.py`
- Create: `src/transkript_bot/services/commands.py`
- Create: `src/transkript_bot/services/keyboard.py`
- Test: `tests/test_commands.py`
- Test: `tests/test_keyboard.py`

**Step 1: Write the failing tests**

```python
# tests/test_commands.py
from transkript_bot.services.commands import parse_user_id

def test_parse_user_id():
    assert parse_user_id("/allow 123") == 123
    assert parse_user_id("/deny 999") == 999
```

```python
# tests/test_keyboard.py
from transkript_bot.services.keyboard import build_chat_settings_keyboard

def test_chat_settings_keyboard():
    chat = {"enabled": True, "allowed_senders": "all", "require_reply": False}
    kb = build_chat_settings_keyboard(chat)
    assert kb is not None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_commands.py tests/test_keyboard.py -v`  
Expected: FAIL (missing modules/functions).

**Step 3: Write minimal implementation**

- `services/commands.py`: parsing helpers for `/allow <id>`, `/deny <id>` and common validation.
- `services/keyboard.py`: build inline keyboards for chat settings toggles.
- Routers:
  - `/start`, `/help`, `/status` in `routers/common.py`.
  - Root-admin commands in `routers/admin.py`: `/admin`, `/allow <id>`, `/deny <id>`, `/stats`, `/system`.
  - Chat admin commands in `routers/chat_admin.py`: `/bot_on`, `/bot_off`, `/bot_settings` with inline keyboard callbacks.
  - Media handler in `routers/media.py` to enqueue jobs and send initial queue message.
- `bot.py` wires routers and starts polling.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_commands.py tests/test_keyboard.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/bot.py src/transkript_bot/routers/common.py src/transkript_bot/routers/admin.py src/transkript_bot/routers/chat_admin.py src/transkript_bot/routers/media.py src/transkript_bot/services/commands.py src/transkript_bot/services/keyboard.py tests/test_commands.py tests/test_keyboard.py
git commit -m "feat: add bot routers and commands"
```

---

### Task 11: Queue worker and progress updates

**Files:**
- Create: `src/transkript_bot/worker.py`
- Modify: `src/transkript_bot/bot.py`
- Create: `src/transkript_bot/services/progress.py`
- Test: `tests/test_progress.py`

**Step 1: Write the failing test**

```python
# tests/test_progress.py
from transkript_bot.services.progress import format_progress

def test_format_progress():
    text = format_progress(stage="transcribing", position=2, eta=120)
    assert "transcribing" in text
    assert "ETA" in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_progress.py -v`  
Expected: FAIL (missing module/function).

**Step 3: Write minimal implementation**

- `services/progress.py`: `format_progress(stage, position, eta)` returns human-readable text.
- `worker.py` implements `process_job()` pipeline:
  - download file from Telegram
  - convert to wav via ffmpeg
  - transcribe (backend selection)
  - format outputs (TXT/MD/JSON)
  - send documents
  - cleanup temp files
- Update job status in DB.
- Edit progress message after each stage.
- Start queue worker task in `bot.py` startup.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_progress.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/worker.py src/transkript_bot/bot.py src/transkript_bot/services/progress.py tests/test_progress.py
git commit -m "feat: add worker pipeline and progress updates"
```

---

### Task 12: Idle shutdown

**Files:**
- Create: `src/transkript_bot/services/idle_shutdown.py`
- Modify: `src/transkript_bot/bot.py`
- Test: `tests/test_idle_shutdown.py`

**Step 1: Write the failing test**

```python
# tests/test_idle_shutdown.py
from transkript_bot.services.idle_shutdown import should_shutdown

def test_should_shutdown():
    assert should_shutdown(last_activity_sec=400, idle_limit_sec=300) is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_idle_shutdown.py -v`  
Expected: FAIL (missing module/function).

**Step 3: Write minimal implementation**

- `idle_shutdown.py` with `should_shutdown()` and `idle_shutdown_loop()` (async) that exits after N minutes idle.
- Start the loop at bot startup.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_idle_shutdown.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/transkript_bot/services/idle_shutdown.py src/transkript_bot/bot.py tests/test_idle_shutdown.py
git commit -m "feat: add idle shutdown loop"
```

---

### Task 13: Colab notebook

**Files:**
- Create: `colab.ipynb`

**Steps:**
1. Create a minimal notebook with 4 cells.
2. Cell 1: Optional Drive mount (commented by default).
3. Cell 2: Prompt for `BOT_TOKEN` and `HF_TOKEN` via `getpass()`.
4. Cell 3: `git clone`, `cd`, install deps with `uv pip` or `pip`.
5. Cell 4: Run `python -m transkript_bot.main`.

**Step 6: Commit**

```bash
git add colab.ipynb
git commit -m "feat: add colab bootstrap notebook"
```

---

### Task 14: Documentation

**Files:**
- Create: `README.md`
- Create: `docs/ADMIN.md`

**Steps:**
1. Add setup instructions (local + Colab) and dependency requirements (ffmpeg, GPU optional).
2. Document environment variables and commands.
3. Describe admin panel workflow and chat settings, including allowlist and chat admin privileges.

**Step 6: Commit**

```bash
git add README.md docs/ADMIN.md
git commit -m "docs: add setup and admin docs"
```

---

## Testing Plan
- Run unit tests during each task (TDD).
- Final run: `pytest -v`.
- Manual smoke test: start bot locally, send a short audio, confirm queue/progress/result.
