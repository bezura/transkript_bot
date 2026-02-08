from __future__ import annotations

from aiogram import Bot

from ..config import Settings
from .keyboard import build_request_action_keyboard


def _request_label(kind: str, target_id: int, title: str | None) -> str:
    if kind == "chat" and title:
        return f"{title} ({target_id})"
    return str(target_id)


async def notify_root_admins_request(
    bot: Bot,
    settings: Settings,
    *,
    kind: str,
    request_id: int,
    target_id: int,
    title: str | None = None,
) -> None:
    text = f"New {kind} request: {_request_label(kind, target_id, title)}"
    keyboard = build_request_action_keyboard(kind=kind, request_id=request_id)
    for admin_id in settings.root_admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=keyboard)
        except Exception:
            continue
