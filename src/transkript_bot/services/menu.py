from __future__ import annotations

from enum import Enum


class MenuRole(str, Enum):
    USER = "user"
    CHAT_ADMIN = "chat_admin"
    ROOT_ADMIN = "root_admin"


def build_help_text(*, role: MenuRole, in_private: bool) -> str:
    lines: list[str] = [
        "Commands:",
        "/menu - open menu",
        "/help - show this help",
        "/status - show queue status",
    ]
    if role == MenuRole.CHAT_ADMIN and not in_private:
        lines.extend(
            [
                "Admins:",
                "/bot_on - enable bot in this chat",
                "/bot_off - disable bot in this chat",
                "/bot_settings - chat settings",
            ]
        )
    if role == MenuRole.ROOT_ADMIN and in_private:
        lines.extend(
            [
                "Root admin:",
                "/admin - toggle admin mode",
                "/allow <id> - allow user",
                "/deny <id> - block user",
                "/stats - show stats",
                "/system - system info",
            ]
        )
    return "\n".join(lines)
