# Telegram Transcription Bot Design (Aiogram v3)

## Summary
Build a Telegram bot (aiogram v3) that transcribes audio/video of any format into text with speaker diarization, usable in private chats and in groups/supergroups (including topics). Access is restricted to an allowlist plus chat admins. The bot runs in Colab or locally, selects the best transcription backend per platform (GPU/WhisperX vs CPU/MPS/faster-whisper), and provides admin controls, queueing, progress updates, and automatic shutdown after idle time.

## Goals
- Accept audio/video from Telegram and return transcription with speaker separation.
- Work in private chats and in groups/supergroups with topics.
- Restrict usage to allowlisted users, with chat admins auto-allowed in their chat.
- Provide queueing with position and ETA, plus progress updates.
- Return results as three files: TXT, MD, JSON.
- Run in Colab with an .ipynb bootstrap, and auto-shutdown after idle.
- Provide an admin panel (root admin) with system info and resource usage.

## Non-Goals
- Horizontal scaling across multiple GPUs or external brokers.
- Long-term storage of media files (deleted after delivery).
- Public self-service access requests.

## Architecture Overview
- Single process (monolith): aiogram bot + in-memory queue + worker coroutine.
- Jobs are persisted to SQLite for durability; media files stored in a temp/work directory.
- Backend selection:
  - GPU (CUDA detected): WhisperX CLI (as in template.py).
  - CPU or Apple Silicon (MPS where available): faster-whisper (ctranslate2).
  - Diarization enabled by default if HF token is configured and backend supports it.
- Colab: notebook clones repo, installs deps, prompts for secrets, runs bot.

## Components
1. **Bot Interface (aiogram v3)**
   - Handles messages, commands, and callback queries.
   - Distinguishes private vs group/supergroup.
   - For topics: replies in the same `message_thread_id`.

2. **Access Control**
   - Global allowlist (root admin managed).
   - Chat admins auto-allowed within their chat.
   - Chat settings allow/deny by sender mode:
     - `all` (no sender filtering)
     - `whitelist` (allowlist only)
     - `list` (explicit user list per chat)

3. **Queue + Worker**
   - In-memory queue (asyncio.Queue) with one worker (global single task).
   - Jobs persisted to SQLite (`queued`, `running`, `done`, `failed`).
   - Queue response includes: position and ETA based on historical average.

4. **Transcription Engine**
   - Media download via Telegram API to local temp dir.
   - ffmpeg converts input to 16kHz mono WAV.
   - Backend execution:
     - WhisperX CLI via subprocess.
     - faster-whisper Python API.
   - JSON output used to generate TXT and MD.

5. **Progress Reporting**
   - The bot edits the initial status message during processing:
     - Downloading
     - Extracting audio
     - Transcribing
     - Diarization (if enabled)
     - Formatting
     - Uploading results

6. **Admin Panel**
   - Root admin only, accessible in private chat.
   - Toggle admin mode (`/admin`) so admin messages are not noisy by default.
   - Features: users allow/deny, chat settings overview, stats, system info, limits.
   - System info includes CPU, RAM, disk, Python, OS, CUDA/GPU if available.

7. **Auto-shutdown**
   - Background task checks idle time (queue empty, no active job).
   - After N minutes (default 5), bot exits cleanly.
   - Designed to conserve Colab compute limits.

## Data Model (SQLite)
- `users`:
  - `tg_id` (PK), `is_allowed`, `is_blocked`, `note`, `created_at`
- `chats`:
  - `chat_id` (PK), `title`, `type`, `enabled`, `allowed_senders`,
    `allowed_user_ids` (JSON), `require_reply`, `language`, `created_at`
- `jobs`:
  - `id` (PK), `chat_id`, `user_id`, `message_id`, `thread_id`,
    `file_id`, `file_name`, `duration_sec`, `backend`, `status`,
    `queued_at`, `started_at`, `finished_at`, `error`, `output_paths` (JSON)

## Chat Behavior
- Default: bot disabled in new groups; admins must enable.
- Topics: settings stored per chat, but responses sent in same topic.
- Soft limits: warn if media exceeds duration/size; admin can confirm.
- For large outputs: send as documents (TXT, MD, JSON) to avoid message limits.

## Configuration
- `.env`:
  - `BOT_TOKEN` (required)
  - `ROOT_ADMIN_IDS` (comma-separated)
  - `HF_TOKEN` (optional)
  - `STORAGE_PATH` (default: `./data/bot.db` or Drive path in Colab)
  - `MEDIA_DIR` (temp dir)
  - `IDLE_SHUTDOWN_MINUTES` (default 5)
  - `DEFAULT_LANGUAGE` (auto)
  - `BACKEND_FORCE` (optional: `whisperx|faster`)

## Error Handling
- Backend failures are caught and the job is marked `failed` with error text.
- User receives an error message and is advised to retry.
- If diarization fails, fallback to non-diarized transcript (if possible).

## Testing
- Unit tests for:
  - Access control decisions.
  - Chat settings logic.
  - ETA calculation.
  - Backend selection detection.
- Smoke test:
  - Run bot locally with a sample audio file.
- Colab test:
  - Execute notebook to verify install and run loop.

## Deliverables
- aiogram v3 bot implementation
- Colab `.ipynb` bootstrap in repo root
- SQLite schema and migration init
- Documentation for setup and admin commands
