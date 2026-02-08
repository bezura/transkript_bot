from __future__ import annotations

import asyncio
import time
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from .config import Settings
from .routers import admin, chat_admin, common, media
from .services.telegram_api import build_api_server
from .services.idle_shutdown import idle_shutdown_loop
from .services.commands import build_command_scopes
from .services.system_info import format_startup_info, get_system_info
from .storage.db import Storage, init_db
from .transcription.backend import choose_backend
from .worker import worker_loop


async def create_app() -> tuple[Bot, Dispatcher]:
    settings = Settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    await init_db(settings.storage_path)
    storage = Storage(settings.storage_path)
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    app_state: dict[str, Any] = {
        "admin_mode": set(),
        "last_activity": time.time(),
    }

    system_info = get_system_info()
    backend = choose_backend(force=settings.backend_force, has_gpu=system_info.get("has_gpu", False))

    api_server = build_api_server(settings)
    session = AiohttpSession(api=api_server)
    bot = Bot(settings.bot_token, session=session)
    dp = Dispatcher()

    dp["settings"] = settings
    dp["storage"] = storage
    dp["queue"] = queue
    dp["app_state"] = app_state
    dp["system_info"] = system_info
    dp["backend"] = backend

    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(chat_admin.router)
    dp.include_router(media.router)

    async def on_startup(bot: Bot, dispatcher: Dispatcher, **_: Any) -> None:
        for _, (scope, commands) in build_command_scopes(root_admin_ids=settings.root_admin_ids).items():
            await bot.set_my_commands(commands, scope=scope)
        for admin_id in settings.root_admin_ids:
            try:
                await bot.send_message(admin_id, format_startup_info(system_info))
            except Exception:
                continue
        dispatcher["worker_task"] = asyncio.create_task(
            worker_loop(queue, bot, settings, storage, app_state, backend)
        )
        dispatcher["idle_task"] = asyncio.create_task(
            idle_shutdown_loop(queue, app_state, settings.idle_shutdown_minutes * 60)
        )

    async def on_shutdown(dispatcher: Dispatcher, **_: Any) -> None:
        for key in ("worker_task", "idle_task"):
            task = dispatcher.get(key)
            if task:
                task.cancel()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return bot, dp


async def run_bot() -> None:
    bot, dp = await create_app()
    await dp.start_polling(bot)
