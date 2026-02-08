from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.types.chat_member_administrator import ChatMemberAdministrator
from aiogram.types.chat_member_owner import ChatMemberOwner

from ..config import Settings
from ..services.keyboard import build_menu_keyboard
from ..services.menu import MenuRole, build_help_text

router = Router()


def _is_admin_member(member) -> bool:
    return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))


async def _is_chat_admin(message: Message) -> bool:
    if not message.from_user:
        return False
    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return _is_admin_member(member)


async def _resolve_role(message: Message, settings: Settings) -> MenuRole:
    user_id = message.from_user.id if message.from_user else None
    if message.chat.type == "private" and user_id in settings.root_admin_ids:
        return MenuRole.ROOT_ADMIN
    if message.chat.type != "private" and await _is_chat_admin(message):
        return MenuRole.CHAT_ADMIN
    return MenuRole.USER


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Send me audio or video and I will transcribe it.\n"
        "In groups, ask an admin to enable me first."
    )


@router.message(Command("help"))
async def help_cmd(message: Message, settings: Settings) -> None:
    role = await _resolve_role(message, settings)
    text = build_help_text(role=role, in_private=message.chat.type == "private")
    await message.answer(text)


@router.message(Command("menu"))
async def menu_cmd(message: Message, settings: Settings) -> None:
    role = await _resolve_role(message, settings)
    kb = build_menu_keyboard(role=role, in_private=message.chat.type == "private")
    await message.answer("Menu:", reply_markup=kb)


@router.message(Command("status"))
async def status_cmd(message: Message, queue) -> None:
    position = queue.qsize()
    await message.answer(f"Queue length: {position}")


@router.callback_query(F.data == "menu:status")
async def menu_status(query: CallbackQuery, settings: Settings, queue) -> None:
    if not query.message:
        return
    role = await _resolve_role(query.message, settings)
    text = f"Queue length: {queue.qsize()}"
    kb = build_menu_keyboard(role=role, in_private=query.message.chat.type == "private")
    await query.message.edit_text(text, reply_markup=kb)
    await query.answer()


@router.callback_query(F.data == "menu:help")
async def menu_help(query: CallbackQuery, settings: Settings) -> None:
    if not query.message:
        return
    role = await _resolve_role(query.message, settings)
    text = build_help_text(role=role, in_private=query.message.chat.type == "private")
    kb = build_menu_keyboard(role=role, in_private=query.message.chat.type == "private")
    await query.message.edit_text(text, reply_markup=kb)
    await query.answer()
