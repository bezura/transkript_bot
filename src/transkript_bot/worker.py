from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import FSInputFile

from .config import Settings
from .services.progress import format_progress
from .storage.db import Storage
from .transcription.faster_whisper import run_faster_whisper
from .transcription.formatting import segments_to_txt
from .transcription.media import convert_to_wav
from .transcription.whisperx_cli import run_whisperx


async def _edit_progress(bot: Bot, chat_id: int, message_id: int, text: str) -> None:
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
    except Exception:
        return


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
    await storage.update_job(job_id, status="running", started_at=started_at, backend=backend)

    if status_message_id:
        await _edit_progress(
            bot,
            chat_id,
            status_message_id,
            format_progress(stage="downloading"),
        )

    await bot.download(file_id, destination=str(input_path))

    if status_message_id:
        await _edit_progress(
            bot,
            chat_id,
            status_message_id,
            format_progress(stage="converting"),
        )

    convert_to_wav(str(input_path), str(wav_path))

    if status_message_id:
        await _edit_progress(
            bot,
            chat_id,
            status_message_id,
            format_progress(stage="transcribing"),
        )

    if backend == "whisperx":
        segments = run_whisperx(
            str(wav_path),
            str(Path(settings.media_dir)),
            model="large-v2",
            language=settings.default_language,
            diarize=bool(settings.hf_token),
            hf_token=settings.hf_token,
            whisperx_cmd=settings.whisperx_cmd,
        )
    else:
        segments = run_faster_whisper(
            str(wav_path),
            model_size="large-v2",
            language=settings.default_language,
            device="cpu",
            compute_type="int8",
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

    await bot.send_document(
        chat_id,
        document=FSInputFile(str(txt_path)),
        reply_to_message_id=message_id,
        message_thread_id=thread_id,
    )
    await bot.send_document(
        chat_id,
        document=FSInputFile(str(md_path)),
        reply_to_message_id=message_id,
        message_thread_id=thread_id,
    )
    await bot.send_document(
        chat_id,
        document=FSInputFile(str(json_path)),
        reply_to_message_id=message_id,
        message_thread_id=thread_id,
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

    for path in (input_path, wav_path, txt_path, md_path, json_path):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            continue

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
        try:
            await process_job(job, bot, settings, storage, state, backend)
        except Exception as exc:
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
            queue.task_done()
