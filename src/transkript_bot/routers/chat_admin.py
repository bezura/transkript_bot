from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.types.chat_member_administrator import ChatMemberAdministrator
from aiogram.types.chat_member_owner import ChatMemberOwner

from ..services.keyboard import build_chat_settings_keyboard
from ..storage.db import Storage

router = Router()


def _is_admin_member(member) -> bool:
    return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))


async def _is_chat_admin(message: Message) -> bool:
    if not message.from_user:
        return False
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return _is_admin_member(member)


async def _reply_private(message: Message, text: str) -> None:
    if message.chat.type == "private":
        await message.answer(text)
        return
    if message.from_user:
        try:
            await message.bot.send_message(message.from_user.id, text)
        except Exception:
            await message.reply(text)
            return
    await message.reply("Sent to your private chat.")


def _parse_chat_id(data: str, action: str) -> int | None:
    parts = data.split(":")
    if len(parts) != 3:
        return None
    if parts[0] != "chat" or parts[1] != action:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


@router.message(Command("bot_on"))
async def bot_on(message: Message, storage: Storage) -> None:
    if not await _is_chat_admin(message):
        return
    await storage.upsert_chat(chat_id=message.chat.id, title=message.chat.title, type_=message.chat.type)
    await storage.set_chat_enabled(message.chat.id, True)
    await _reply_private(message, "Bot enabled in this chat")


@router.message(Command("bot_off"))
async def bot_off(message: Message, storage: Storage) -> None:
    if not await _is_chat_admin(message):
        return
    await storage.upsert_chat(chat_id=message.chat.id, title=message.chat.title, type_=message.chat.type)
    await storage.set_chat_enabled(message.chat.id, False)
    await _reply_private(message, "Bot disabled in this chat")


@router.message(Command("bot_settings"))
async def bot_settings(message: Message, storage: Storage) -> None:
    if not await _is_chat_admin(message):
        return
    await storage.upsert_chat(chat_id=message.chat.id, title=message.chat.title, type_=message.chat.type)
    chat = await storage.get_chat(message.chat.id)
    if not chat:
        await _reply_private(message, "Chat not found")
        return
    kb = build_chat_settings_keyboard(chat)
    if message.chat.type == "private":
        await message.answer("Chat settings:", reply_markup=kb)
        return
    if message.from_user:
        try:
            await message.bot.send_message(message.from_user.id, "Chat settings:", reply_markup=kb)
            await message.reply("Sent to your private chat.")
            return
        except Exception:
            await message.reply("Unable to open private chat.")

@router.callback_query(F.data.startswith("chat:toggle_enabled:"))
async def toggle_enabled(query: CallbackQuery, storage: Storage) -> None:
    if not query.message:
        return
    chat_id = _parse_chat_id(query.data, "toggle_enabled")
    if chat_id is None:
        await query.answer("Invalid action", show_alert=True)
        return
    chat = await storage.get_chat(chat_id)
    if not chat:
        await query.answer("Chat not found", show_alert=True)
        return
    new_value = not chat["enabled"]
    await storage.set_chat_enabled(chat_id, new_value)
    updated = await storage.get_chat(chat_id)
    if updated:
        await query.message.edit_reply_markup(reply_markup=build_chat_settings_keyboard(updated))
    await query.answer("Updated")


@router.callback_query(F.data.startswith("chat:toggle_allowed:"))
async def toggle_allowed(query: CallbackQuery, storage: Storage) -> None:
    if not query.message:
        return
    chat_id = _parse_chat_id(query.data, "toggle_allowed")
    if chat_id is None:
        await query.answer("Invalid action", show_alert=True)
        return
    chat = await storage.get_chat(chat_id)
    if not chat:
        await query.answer("Chat not found", show_alert=True)
        return
    current = chat.get("allowed_senders", "whitelist")
    next_value = "all" if current == "whitelist" else "whitelist"
    await storage.set_chat_allowed_senders(chat_id, next_value)
    updated = await storage.get_chat(chat_id)
    if updated:
        await query.message.edit_reply_markup(reply_markup=build_chat_settings_keyboard(updated))
    await query.answer("Updated")


@router.callback_query(F.data.startswith("chat:toggle_reply:"))
async def toggle_reply(query: CallbackQuery, storage: Storage) -> None:
    if not query.message:
        return
    chat_id = _parse_chat_id(query.data, "toggle_reply")
    if chat_id is None:
        await query.answer("Invalid action", show_alert=True)
        return
    chat = await storage.get_chat(chat_id)
    if not chat:
        await query.answer("Chat not found", show_alert=True)
        return
    new_value = not chat.get("require_reply", False)
    await storage.set_chat_require_reply(chat_id, new_value)
    updated = await storage.get_chat(chat_id)
    if updated:
        await query.message.edit_reply_markup(reply_markup=build_chat_settings_keyboard(updated))
    await query.answer("Updated")
