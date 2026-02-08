from __future__ import annotations

from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)


def parse_user_id(text: str) -> int | None:
    parts = text.strip().split()
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _cmds(items: list[tuple[str, str]]) -> list[BotCommand]:
    return [BotCommand(command=name, description=desc) for name, desc in items]


def build_command_scopes(*, root_admin_ids: set[int]) -> dict[str, tuple[object, list[BotCommand]]]:
    base_cmds = _cmds(
        [
            ("menu", "Open menu"),
            ("help", "Show help"),
            ("status", "Show queue status"),
        ]
    )
    admin_cmds = _cmds(
        [
            ("bot_on", "Enable bot in chat"),
            ("bot_off", "Disable bot in chat"),
            ("bot_settings", "Chat settings"),
        ]
    )
    root_cmds = _cmds(
        [
            ("admin", "Toggle admin mode"),
            ("allow", "Allow user"),
            ("deny", "Block user"),
            ("stats", "Show stats"),
            ("system", "System info"),
        ]
    )
    scopes: dict[str, tuple[object, list[BotCommand]]] = {
        "all_private_chats": (BotCommandScopeAllPrivateChats(), base_cmds),
        "all_group_chats": (BotCommandScopeAllGroupChats(), base_cmds),
        "all_chat_administrators": (BotCommandScopeAllChatAdministrators(), base_cmds + admin_cmds),
    }
    for admin_id in root_admin_ids:
        scopes[f"root_admin:{admin_id}"] = (
            BotCommandScopeChat(chat_id=admin_id),
            base_cmds + root_cmds,
        )
    return scopes
