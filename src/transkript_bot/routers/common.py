from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Send me audio or video and I will transcribe it.\n"
        "In groups, ask an admin to enable me first."
    )


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(
        "Commands:\n"
        "/status - show queue status\n"
        "Admins: /bot_on, /bot_off, /bot_settings\n"
        "Root admin: /allow <id>, /deny <id>, /stats, /system"
    )


@router.message(Command("status"))
async def status_cmd(message: Message, queue) -> None:
    position = queue.qsize()
    await message.answer(f"Queue length: {position}")
