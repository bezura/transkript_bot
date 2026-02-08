from __future__ import annotations

import time
from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from aiogram.types.chat_member_administrator import ChatMemberAdministrator
from aiogram.types.chat_member_owner import ChatMemberOwner

from ..config import Settings
from ..services.access import can_process
from ..services.queue import estimate_eta
from ..storage.db import Storage

router = Router()


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
        }
    if message.video:
        return {
            "file_id": message.video.file_id,
            "file_name": message.video.file_name or "video",
            "duration": message.video.duration,
        }
    if message.voice:
        return {
            "file_id": message.voice.file_id,
            "file_name": "voice.ogg",
            "duration": message.voice.duration,
        }
    if message.document:
        return {
            "file_id": message.document.file_id,
            "file_name": message.document.file_name or "document",
            "duration": None,
        }
    return None


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

    is_admin = await _is_chat_admin(message) if message.chat.type != "private" else False

    if message.chat.type == "private":
        user = await storage.get_user(message.from_user.id if message.from_user else 0)
        if not user or user.get("is_blocked"):
            await message.reply("Access denied")
            return
        if not user.get("is_allowed"):
            await message.reply("You are not allowed to use this bot")
            return
        chat_cfg = {"enabled": True, "allowed_senders": "whitelist", "allowed_user_ids": []}
    else:
        await storage.upsert_chat(chat_id=message.chat.id, title=message.chat.title, type_=message.chat.type)
        chat = await storage.get_chat(message.chat.id)
        if not chat or not chat.get("enabled"):
            return
        user = await storage.get_user(message.from_user.id if message.from_user else 0)
        user_allowed = bool(user and user.get("is_allowed"))
        if user and user.get("is_blocked"):
            await message.reply("Access denied")
            return
        if not can_process(user_allowed=user_allowed, is_chat_admin=is_admin, chat=chat):
            return
        if chat.get("require_reply"):
            if not message.reply_to_message or message.reply_to_message.from_user.id != message.bot.id:
                await message.reply("Please reply to the bot to start transcription")
                return
        chat_cfg = chat

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

    app_state["last_activity"] = time.time()
