from typing import Any


def can_process(*, user_allowed: bool, is_chat_admin: bool, chat: dict[str, Any]) -> bool:
    if not chat.get("enabled", False):
        return False
    if is_chat_admin:
        return True
    mode = chat.get("allowed_senders", "whitelist")
    if mode == "all":
        return True
    if mode == "whitelist":
        return user_allowed
    if mode == "list":
        return False
    return False
