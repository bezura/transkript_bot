from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
