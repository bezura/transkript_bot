from __future__ import annotations

from aiogram.client.telegram import PRODUCTION, TelegramAPIServer

from ..config import Settings


def build_api_server(settings: Settings) -> TelegramAPIServer:
    base_url = settings.bot_api_base_url
    if not base_url:
        return PRODUCTION
    return TelegramAPIServer.from_base(base_url, is_local=True)
