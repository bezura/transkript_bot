from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_chat_settings_keyboard(chat: dict) -> InlineKeyboardMarkup:
    enabled = chat.get("enabled", False)
    allowed = chat.get("allowed_senders", "whitelist")
    require_reply = chat.get("require_reply", False)

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"Enabled: {'on' if enabled else 'off'}",
        callback_data="chat:toggle_enabled",
    )
    builder.button(
        text=f"Allowed: {allowed}",
        callback_data="chat:toggle_allowed",
    )
    builder.button(
        text=f"Reply only: {'yes' if require_reply else 'no'}",
        callback_data="chat:toggle_reply",
    )
    builder.adjust(1)
    return builder.as_markup()
