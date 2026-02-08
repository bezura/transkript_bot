from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import Settings
from ..services.commands import parse_user_id
from ..services.system_info import format_startup_info, get_system_info
from ..storage.db import Storage

router = Router()


def _is_root_admin(user_id: int | None, settings: Settings) -> bool:
    if user_id is None:
        return False
    return user_id in settings.root_admin_ids


def _is_private(message: Message) -> bool:
    return message.chat.type == "private"


async def _reply_private(message: Message, text: str) -> None:
    if _is_private(message):
        await message.answer(text)
        return
    if message.from_user:
        await message.bot.send_message(message.from_user.id, text)
    await message.reply("Sent to your private chat.")


@router.message(Command("admin"))
async def admin_toggle(message: Message, settings: Settings, state: dict) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    admins = state.setdefault("admin_mode", set())
    uid = message.from_user.id if message.from_user else 0
    if uid in admins:
        admins.remove(uid)
        await _reply_private(message, "Admin mode: OFF")
    else:
        admins.add(uid)
        await _reply_private(message, "Admin mode: ON")


@router.message(Command("allow"))
async def allow_user(message: Message, settings: Settings, storage: Storage) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    target = parse_user_id(message.text or "")
    if target is None:
        await _reply_private(message, "Usage: /allow <user_id>")
        return
    await storage.set_user_allowed(target, True)
    await storage.set_user_blocked(target, False)
    await _reply_private(message, f"User {target} allowed")


@router.message(Command("deny"))
async def deny_user(message: Message, settings: Settings, storage: Storage) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    target = parse_user_id(message.text or "")
    if target is None:
        await _reply_private(message, "Usage: /deny <user_id>")
        return
    await storage.set_user_allowed(target, False)
    await storage.set_user_blocked(target, True)
    await _reply_private(message, f"User {target} blocked")


@router.message(Command("stats"))
async def stats(message: Message, settings: Settings, storage: Storage) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    stats_data = await storage.get_stats()
    text = (
        "Stats:\n"
        f"Users: {stats_data['users_total']} (allowed {stats_data['users_allowed']}, blocked {stats_data['users_blocked']})\n"
        f"Chats: {stats_data['chats_total']}\n"
        f"Jobs: {stats_data['jobs_total']}"
    )
    await _reply_private(message, text)


@router.message(Command("system"))
async def system_info_cmd(message: Message, settings: Settings) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    info = get_system_info()
    await _reply_private(message, format_startup_info(info))
