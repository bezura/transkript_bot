from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from .config import Settings
from .services.progress import format_progress
from .services.keyboard import build_result_files_keyboard
from .storage.db import Storage
from .transcription.faster_whisper import run_faster_whisper
from .transcription.formatting import segments_to_txt
from .transcription.media import convert_to_wav
from .transcription.whisperx_cli import run_whisperx

logger = logging.getLogger(__name__)


async def _edit_progress(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )
        return True
    except Exception:
        return False


def _safe_suffix(file_name: str | None) -> str:
    if not file_name:
        return ".bin"
    suffix = Path(file_name).suffix
    return suffix or ".bin"


async def process_job(
    job: dict[str, Any],
    bot: Bot,
    settings: Settings,
    storage: Storage,
    state: dict[str, Any],
    backend: str,
) -> None:
    job_id = job["id"]
    chat_id = job["chat_id"]
    message_id = job["message_id"]
    thread_id = job.get("thread_id")
    status_message_id = job.get("status_message_id")
    file_id = job["file_id"]
    file_name = job.get("file_name")

    os.makedirs(settings.media_dir, exist_ok=True)
    suffix = _safe_suffix(file_name)
    input_path = Path(settings.media_dir) / f"{job_id}{suffix}"
    wav_path = Path(settings.media_dir) / f"{job_id}.wav"
    txt_path = Path(settings.media_dir) / f"{job_id}.txt"
    md_path = Path(settings.media_dir) / f"{job_id}.md"
    json_path = Path(settings.media_dir) / f"{job_id}.json"

    started_at = time.time()
    logger.info(
        "Job %s started (chat=%s message=%s backend=%s file=%s)",
        job_id,
        chat_id,
        message_id,
        backend,
        file_name or file_id,
    )
    await storage.update_job(job_id, status="running", started_at=started_at, backend=backend)

    if status_message_id:
        await _edit_progress(
            bot,
            chat_id,
            status_message_id,
            format_progress(stage="downloading"),
        )

    logger.info("Job %s downloading file_id=%s", job_id, file_id)
    await bot.download(file_id, destination=str(input_path))

    if status_message_id:
        await _edit_progress(
            bot,
            chat_id,
            status_message_id,
            format_progress(stage="converting"),
        )

    logger.info("Job %s converting to wav: %s -> %s", job_id, input_path, wav_path)
    convert_to_wav(str(input_path), str(wav_path))

    if status_message_id:
        await _edit_progress(
            bot,
            chat_id,
            status_message_id,
            format_progress(stage="transcribing"),
        )

    logger.info("Job %s transcribing with backend=%s", job_id, backend)
    transcribe_started_at = time.time()
    loop = asyncio.get_running_loop()
    last_progress_percent = -1
    last_progress_edit_at = 0.0

    def _transcribe_progress_callback(percent: int) -> None:
        nonlocal last_progress_percent, last_progress_edit_at
        percent = max(0, min(99, int(percent)))
        now = time.time()
        if percent <= last_progress_percent:
            return
        if percent < 99 and now - last_progress_edit_at < 1.0:
            return
        last_progress_percent = percent
        last_progress_edit_at = now
        if not status_message_id:
            return
        text = format_progress(stage="transcribing", transcribe_percent=percent)
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(
                _edit_progress(
                    bot,
                    chat_id,
                    status_message_id,
                    text,
                )
            )
        )

    if backend == "whisperx":
        segments = await asyncio.to_thread(
            run_whisperx,
            str(wav_path),
            str(Path(settings.media_dir)),
            model=settings.whisper_model,
            language=settings.default_language,
            diarize=bool(settings.hf_token),
            hf_token=settings.hf_token,
            whisperx_cmd=settings.whisperx_cmd,
        )
    else:
        segments = await asyncio.to_thread(
            run_faster_whisper,
            str(wav_path),
            model_size=settings.whisper_model,
            language=settings.default_language,
            device="cpu",
            compute_type="int8",
            on_progress=_transcribe_progress_callback,
        )
    logger.info(
        "Job %s transcription completed in %.2fs (segments=%s)",
        job_id,
        time.time() - transcribe_started_at,
        len(segments),
    )

    text = segments_to_txt(segments)
    txt_path.write_text(text, encoding="utf-8")
    md_path.write_text(text, encoding="utf-8")
    json_path.write_text(json.dumps({"segments": segments}, ensure_ascii=False), encoding="utf-8")

    if status_message_id:
        await _edit_progress(
            bot,
            chat_id,
            status_message_id,
            format_progress(stage="uploading"),
        )

    logger.info("Job %s updating status message with result selector keyboard", job_id)
    keyboard = build_result_files_keyboard(job_id=job_id)
    final_text = format_progress(stage="done", transcribe_percent=100)
    if status_message_id:
        updated = await _edit_progress(
            bot,
            chat_id,
            status_message_id,
            final_text,
            reply_markup=keyboard,
        )
        if not updated:
            await bot.send_message(
                chat_id,
                final_text,
                reply_to_message_id=message_id,
                message_thread_id=thread_id,
                reply_markup=keyboard,
            )
    else:
        await bot.send_message(
            chat_id,
            final_text,
            reply_to_message_id=message_id,
            message_thread_id=thread_id,
            reply_markup=keyboard,
        )

    finished_at = time.time()
    await storage.update_job(
        job_id,
        status="done",
        finished_at=finished_at,
        output_paths=json.dumps(
            {"txt": str(txt_path), "md": str(md_path), "json": str(json_path)}
        ),
    )

    for path in (input_path, wav_path):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            continue

    logger.info("Job %s completed in %.2fs", job_id, finished_at - started_at)
    state["last_activity"] = time.time()


async def worker_loop(
    queue,
    bot: Bot,
    settings: Settings,
    storage: Storage,
    state: dict[str, Any],
    backend: str,
) -> None:
    while True:
        job = await queue.get()
        logger.info("Picked job from queue: id=%s", job.get("id"))
        state["worker_busy"] = True
        try:
            await process_job(job, bot, settings, storage, state, backend)
        except Exception as exc:
            logger.exception("Job %s failed: %s", job.get("id"), exc)
            await storage.update_job(job["id"], status="failed", error=str(exc))
            status_message_id = job.get("status_message_id")
            if status_message_id:
                await _edit_progress(
                    bot,
                    job["chat_id"],
                    status_message_id,
                    f"Failed: {exc}",
                )
        finally:
            state["worker_busy"] = False
            queue.task_done()
