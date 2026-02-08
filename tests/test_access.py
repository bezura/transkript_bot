from transkript_bot.services.access import can_process


def test_allowlist_only():
    chat = {"enabled": True, "allowed_senders": "whitelist", "allowed_user_ids": []}
    assert can_process(user_allowed=True, is_chat_admin=False, chat=chat) is True
    assert can_process(user_allowed=False, is_chat_admin=False, chat=chat) is False
