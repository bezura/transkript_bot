from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.types.chat_member_administrator import ChatMemberAdministrator
from aiogram.types.chat_member_owner import ChatMemberOwner

from ..config import Settings
from ..services.access import can_process
from ..services.limits import is_cloud_file_too_large
from ..services.queue import estimate_eta
from ..services.keyboard import build_request_access_keyboard
from ..services.notifications import notify_root_admins_request
from ..storage.db import Storage

router = Router()
logger = logging.getLogger(__name__)


def _is_admin_member(member) -> bool:
    return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))


async def _is_chat_admin(message: Message) -> bool:
    if not message.from_user:
        return False
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return _is_admin_member(member)


def _extract_media(message: Message) -> dict[str, Any] | None:
    if message.audio:
        return {
            "file_id": message.audio.file_id,
            "file_name": message.audio.file_name or "audio",
            "duration": message.audio.duration,
            "file_size": message.audio.file_size,
        }
    if message.video:
        return {
            "file_id": message.video.file_id,
            "file_name": message.video.file_name or "video",
            "duration": message.video.duration,
            "file_size": message.video.file_size,
        }
    if message.voice:
        return {
            "file_id": message.voice.file_id,
            "file_name": "voice.ogg",
            "duration": message.voice.duration,
            "file_size": message.voice.file_size,
        }
    if message.document:
        return {
            "file_id": message.document.file_id,
            "file_name": message.document.file_name or "document",
            "duration": None,
            "file_size": message.document.file_size,
        }
    return None


def _is_meeting_webm(file_name: str | None) -> bool:
    if not file_name:
        return False
    normalized = file_name.casefold()
    return (normalized.endswith(".webm") or normalized.endswith(".mp4")) and "meeting" in normalized


async def create_user_request(storage: Storage, user_id: int) -> tuple[int, bool]:
    existing = await storage.get_pending_request(kind="user", user_id=user_id, chat_id=None)
    if existing:
        return int(existing["id"]), False
    request_id = await storage.create_request(
        kind="user",
        user_id=user_id,
        chat_id=None,
        requested_by_id=user_id,
    )
    return request_id, True


@router.callback_query(F.data == "menu:request_user")
async def request_user_access(query: CallbackQuery, storage: Storage, settings: Settings) -> None:
    if not query.from_user:
        await query.answer("Unknown user", show_alert=True)
        return
    request_id, created = await create_user_request(storage, query.from_user.id)
    if created:
        await notify_root_admins_request(
            query.bot,
            settings,
            kind="user",
            request_id=request_id,
            target_id=query.from_user.id,
        )
    await query.answer("Access request sent" if created else "Request already pending")


def _parse_result_file_callback(data: str | None) -> tuple[int, str] | None:
    if not data:
        return None
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != "job" or parts[1] != "file":
        return None
    try:
        return int(parts[2]), parts[3]
    except ValueError:
        return None


@router.callback_query(F.data.startswith("job:file:"))
async def send_result_file(query: CallbackQuery, storage: Storage, app_state: dict) -> None:
    parsed = _parse_result_file_callback(query.data)
    if not parsed or not query.message:
        await query.answer("Invalid action", show_alert=True)
        return

    job_id, file_kind = parsed
    job = await storage.get_job(job_id)
    if not job:
        await query.answer("Job not found", show_alert=True)
        return
    if int(job.get("chat_id", 0)) != query.message.chat.id:
        await query.answer("Access denied", show_alert=True)
        return

    output_paths_raw = job.get("output_paths")
    try:
        output_paths = json.loads(output_paths_raw) if output_paths_raw else {}
    except json.JSONDecodeError:
        output_paths = {}
    if not isinstance(output_paths, dict):
        output_paths = {}

    selector_key = (query.message.chat.id, query.message.message_id)
    sent_files_state = app_state.setdefault("result_file_messages", {})
    previous_message_ids = sent_files_state.get(selector_key, [])
    for message_id in previous_message_ids:
        try:
            await query.bot.delete_message(chat_id=query.message.chat.id, message_id=message_id)
        except Exception:
            continue

    kinds = ("txt", "md", "json") if file_kind == "all" else (file_kind,)
    sent = 0
    new_message_ids: list[int] = []
    for kind in kinds:
        path = output_paths.get(kind)
        if not path or not Path(path).is_file():
            continue
        try:
            sent_message = await query.bot.send_document(
                chat_id=query.message.chat.id,
                document=FSInputFile(path),
                message_thread_id=query.message.message_thread_id,
            )
        except TelegramBadRequest as exc:
            if "message thread not found" not in str(exc).lower():
                raise
            sent_message = await query.bot.send_document(
                chat_id=query.message.chat.id,
                document=FSInputFile(path),
            )
        new_message_ids.append(sent_message.message_id)
        sent += 1

    if sent == 0:
        await query.answer("Result files are unavailable", show_alert=True)
        return
    sent_files_state[selector_key] = new_message_ids
    await query.answer(f"Sent {sent} file(s)")

@router.message(F.audio | F.video | F.voice | F.document)
async def handle_media(
    message: Message,
    settings: Settings,
    storage: Storage,
    queue,
    app_state: dict,
) -> None:
    media = _extract_media(message)
    if not media:
        return
    if message.chat.type != "private" and not _is_meeting_webm(media.get("file_name")):
        logger.info(
            "Media ignored by filename rule: chat_id=%s file=%s",
            message.chat.id,
            media.get("file_name"),
        )
        return

    is_admin = await _is_chat_admin(message) if message.chat.type != "private" else False

    if message.chat.type == "private":
        user_id = message.from_user.id if message.from_user else 0
        user = await storage.get_user(user_id)
        if user and user.get("is_blocked"):
            logger.info("Media rejected: blocked user_id=%s", user_id)
            await message.reply("Access denied")
            return
        if not user or not user.get("is_allowed"):
            logger.info("Media rejected: user_id=%s is not allowed", user_id)
            request_id, created = await create_user_request(storage, user_id)
            if created:
                await notify_root_admins_request(
                    message.bot,
                    settings,
                    kind="user",
                    request_id=request_id,
                    target_id=user_id,
                )
            await message.reply(
                "You are not allowed to use this bot",
                reply_markup=build_request_access_keyboard(),
            )
            return
        chat_cfg = {"enabled": True, "allowed_senders": "whitelist", "allowed_user_ids": []}
    else:
        await storage.upsert_chat(chat_id=message.chat.id, title=message.chat.title, type_=message.chat.type)
        chat = await storage.get_chat(message.chat.id)
        if not chat or not chat.get("enabled"):
            logger.info("Media ignored: chat_id=%s is disabled", message.chat.id)
            return
        user = await storage.get_user(message.from_user.id if message.from_user else 0)
        user_allowed = bool(user and user.get("is_allowed"))
        if user and user.get("is_blocked"):
            logger.info("Media rejected in chat: blocked user_id=%s", message.from_user.id if message.from_user else 0)
            await message.reply("Access denied")
            return
        if not can_process(user_allowed=user_allowed, is_chat_admin=is_admin, chat=chat):
            logger.info(
                "Media rejected by chat policy: chat_id=%s user_id=%s is_admin=%s user_allowed=%s mode=%s",
                message.chat.id,
                message.from_user.id if message.from_user else 0,
                is_admin,
                user_allowed,
                chat.get("allowed_senders"),
            )
            return
        chat_cfg = chat

    if not settings.bot_api_base_url and is_cloud_file_too_large(media.get("file_size")):
        logger.warning(
            "Media too large for cloud API: chat_id=%s size_bytes=%s",
            message.chat.id,
            media.get("file_size"),
        )
        await message.reply(
            "File is too large for the cloud Bot API. "
            "Please configure BOT_API_BASE_URL to use a local Bot API server."
        )
        return

    position = queue.qsize() + 1
    durations = await storage.get_recent_durations(limit=5)
    eta = estimate_eta(durations, position)
    eta_text = "unknown" if eta < 0 else f"{eta} sec"

    status_msg = await message.reply(
        f"Queued. Position: {position}. ETA: {eta_text}."
    )

    job_id = await storage.create_job(
        chat_id=message.chat.id,
        user_id=message.from_user.id if message.from_user else 0,
        message_id=message.message_id,
        thread_id=message.message_thread_id,
        file_id=media["file_id"],
        file_name=media["file_name"],
        duration_sec=media.get("duration"),
        status="queued",
        status_message_id=status_msg.message_id,
        progress_message_id=status_msg.message_id,
    )

    await queue.put(
        {
            "id": job_id,
            "chat_id": message.chat.id,
            "thread_id": message.message_thread_id,
            "message_id": message.message_id,
            "file_id": media["file_id"],
            "file_name": media["file_name"],
            "status_message_id": status_msg.message_id,
        }
    )
    logger.info(
        "Queued job id=%s chat_id=%s user_id=%s position=%s file=%s size=%s",
        job_id,
        message.chat.id,
        message.from_user.id if message.from_user else 0,
        position,
        media["file_name"],
        media.get("file_size"),
    )

    app_state["last_activity"] = time.time()
