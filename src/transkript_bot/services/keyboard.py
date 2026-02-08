from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .menu import MenuRole


def build_chat_settings_keyboard(chat: dict) -> InlineKeyboardMarkup:
    enabled = chat.get("enabled", False)
    allowed = chat.get("allowed_senders", "whitelist")
    require_reply = chat.get("require_reply", False)
    chat_id = chat.get("chat_id", 0)

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"Enabled: {'on' if enabled else 'off'}",
        callback_data=f"chat:toggle_enabled:{chat_id}",
    )
    builder.button(
        text=f"Allowed: {allowed}",
        callback_data=f"chat:toggle_allowed:{chat_id}",
    )
    builder.button(
        text=f"Reply only: {'yes' if require_reply else 'no'}",
        callback_data=f"chat:toggle_reply:{chat_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


def build_menu_keyboard(*, role: MenuRole, in_private: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Status", callback_data="menu:status")
    builder.button(text="Help", callback_data="menu:help")
    if role == MenuRole.USER and in_private:
        builder.button(text="Request access", callback_data="menu:request_user")
    if role == MenuRole.CHAT_ADMIN and not in_private:
        builder.button(text="Request chat access", callback_data="menu:request_chat")
    if role == MenuRole.ROOT_ADMIN and in_private:
        builder.button(text="Admin", callback_data="menu:admin")
    builder.adjust(1)
    return builder.as_markup()


def build_request_access_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Request access", callback_data="menu:request_user")
    builder.adjust(1)
    return builder.as_markup()


def build_admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="User requests", callback_data="admin:reqs:user")
    builder.button(text="Chat requests", callback_data="admin:reqs:chat")
    builder.adjust(1)
    return builder.as_markup()


def build_requests_list_keyboard(*, kind: str, requests: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for req in requests:
        target = req.get("user_id") if kind == "user" else req.get("chat_id")
        label = f"{kind} {target}"
        builder.button(
            text=f"Approve {label}",
            callback_data=f"admin:req:{kind}:approve:{req['id']}",
        )
        builder.button(
            text=f"Deny {label}",
            callback_data=f"admin:req:{kind}:deny:{req['id']}",
        )
    builder.button(text="Back", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()
