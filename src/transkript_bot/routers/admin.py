from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..config import Settings
from ..services.keyboard import build_admin_menu_keyboard, build_requests_list_keyboard
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


def _is_admin_mode(app_state: dict, user_id: int) -> bool:
    return user_id in app_state.get("admin_mode", set())


async def approve_user_request(storage: Storage, request_id: int) -> bool:
    req = await storage.get_request(request_id)
    if not req or req.get("kind") != "user":
        return False
    user_id = req.get("user_id")
    if user_id is None:
        return False
    await storage.set_user_allowed(int(user_id), True)
    await storage.set_user_blocked(int(user_id), False)
    await storage.set_request_status(request_id, status="approved")
    return True


async def deny_user_request(storage: Storage, request_id: int) -> bool:
    req = await storage.get_request(request_id)
    if not req or req.get("kind") != "user":
        return False
    user_id = req.get("user_id")
    if user_id is None:
        return False
    await storage.set_user_blocked(int(user_id), True)
    await storage.set_request_status(request_id, status="denied")
    return True


async def approve_chat_request(storage: Storage, request_id: int) -> bool:
    req = await storage.get_request(request_id)
    if not req or req.get("kind") != "chat":
        return False
    chat_id = req.get("chat_id")
    if chat_id is None:
        return False
    await storage.set_chat_enabled(int(chat_id), True)
    await storage.set_chat_allowed_senders(int(chat_id), "whitelist")
    await storage.set_request_status(request_id, status="approved")
    return True


async def deny_chat_request(storage: Storage, request_id: int) -> bool:
    req = await storage.get_request(request_id)
    if not req or req.get("kind") != "chat":
        return False
    chat_id = req.get("chat_id")
    if chat_id is None:
        return False
    await storage.set_chat_enabled(int(chat_id), False)
    await storage.set_request_status(request_id, status="denied")
    return True


async def _reply_private(message: Message, text: str) -> None:
    if _is_private(message):
        await message.answer(text)
        return
    if message.from_user:
        await message.bot.send_message(message.from_user.id, text)
    await message.reply("Sent to your private chat.")


@router.message(Command("admin"))
async def admin_toggle(message: Message, settings: Settings, app_state: dict) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    admins = app_state.setdefault("admin_mode", set())
    uid = message.from_user.id if message.from_user else 0
    if uid in admins:
        admins.remove(uid)
        await _reply_private(message, "Admin mode: OFF")
    else:
        admins.add(uid)
        await _reply_private(message, "Admin mode: ON")


@router.message(Command("allow"))
async def allow_user(message: Message, settings: Settings, storage: Storage, app_state: dict) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    if not _is_admin_mode(app_state, message.from_user.id if message.from_user else 0):
        await _reply_private(message, "Enable admin mode with /admin")
        return
    target = parse_user_id(message.text or "")
    if target is None:
        await _reply_private(message, "Usage: /allow <user_id>")
        return
    await storage.set_user_allowed(target, True)
    await storage.set_user_blocked(target, False)
    await _reply_private(message, f"User {target} allowed")


@router.message(Command("deny"))
async def deny_user(message: Message, settings: Settings, storage: Storage, app_state: dict) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    if not _is_admin_mode(app_state, message.from_user.id if message.from_user else 0):
        await _reply_private(message, "Enable admin mode with /admin")
        return
    target = parse_user_id(message.text or "")
    if target is None:
        await _reply_private(message, "Usage: /deny <user_id>")
        return
    await storage.set_user_allowed(target, False)
    await storage.set_user_blocked(target, True)
    await _reply_private(message, f"User {target} blocked")


@router.message(Command("stats"))
async def stats(message: Message, settings: Settings, storage: Storage, app_state: dict) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    if not _is_admin_mode(app_state, message.from_user.id if message.from_user else 0):
        await _reply_private(message, "Enable admin mode with /admin")
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
async def system_info_cmd(message: Message, settings: Settings, app_state: dict) -> None:
    if not _is_root_admin(message.from_user.id if message.from_user else None, settings):
        return
    if not _is_admin_mode(app_state, message.from_user.id if message.from_user else 0):
        await _reply_private(message, "Enable admin mode with /admin")
        return
    info = get_system_info()
    await _reply_private(message, format_startup_info(info))


@router.callback_query(F.data == "admin:menu")
async def admin_menu(query: CallbackQuery, settings: Settings, app_state: dict) -> None:
    if not _is_root_admin(query.from_user.id if query.from_user else None, settings):
        await query.answer("Admins only", show_alert=True)
        return
    if not _is_admin_mode(app_state, query.from_user.id if query.from_user else 0):
        await query.answer("Enable admin mode with /admin", show_alert=True)
        return
    if query.message:
        await query.message.edit_text("Admin menu:", reply_markup=build_admin_menu_keyboard())
    await query.answer()


@router.callback_query(F.data == "menu:admin")
async def menu_admin(query: CallbackQuery, settings: Settings, app_state: dict) -> None:
    await admin_menu(query, settings, app_state)


@router.callback_query(F.data.startswith("admin:reqs:"))
async def admin_list_requests(
    query: CallbackQuery, settings: Settings, app_state: dict, storage: Storage
) -> None:
    if not _is_root_admin(query.from_user.id if query.from_user else None, settings):
        await query.answer("Admins only", show_alert=True)
        return
    if not _is_admin_mode(app_state, query.from_user.id if query.from_user else 0):
        await query.answer("Enable admin mode with /admin", show_alert=True)
        return
    parts = (query.data or "").split(":")
    if len(parts) != 3:
        await query.answer("Invalid request", show_alert=True)
        return
    kind = parts[2]
    requests = await storage.list_requests(kind=kind, status="pending", limit=10, offset=0)
    text = f"Pending {kind} requests: {len(requests)}"
    if query.message:
        await query.message.edit_text(
            text,
            reply_markup=build_requests_list_keyboard(kind=kind, requests=requests),
        )
    await query.answer()


@router.callback_query(F.data.startswith("admin:req:"))
async def admin_request_action(
    query: CallbackQuery, settings: Settings, app_state: dict, storage: Storage
) -> None:
    if not _is_root_admin(query.from_user.id if query.from_user else None, settings):
        await query.answer("Admins only", show_alert=True)
        return
    if not _is_admin_mode(app_state, query.from_user.id if query.from_user else 0):
        await query.answer("Enable admin mode with /admin", show_alert=True)
        return
    parts = (query.data or "").split(":")
    if len(parts) != 5:
        await query.answer("Invalid request", show_alert=True)
        return
    _, _, kind, action, req_id_raw = parts
    try:
        req_id = int(req_id_raw)
    except ValueError:
        await query.answer("Invalid request", show_alert=True)
        return
    if kind == "user":
        ok = await approve_user_request(storage, req_id) if action == "approve" else await deny_user_request(storage, req_id)
    else:
        ok = await approve_chat_request(storage, req_id) if action == "approve" else await deny_chat_request(storage, req_id)
    if not ok:
        await query.answer("Request not found", show_alert=True)
        return
    requests = await storage.list_requests(kind=kind, status="pending", limit=10, offset=0)
    text = f"Pending {kind} requests: {len(requests)}"
    if query.message:
        await query.message.edit_text(
            text,
            reply_markup=build_requests_list_keyboard(kind=kind, requests=requests),
        )
    await query.answer("Updated")
