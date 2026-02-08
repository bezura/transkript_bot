from transkript_bot.services.keyboard import build_chat_settings_keyboard


def test_chat_settings_keyboard():
    chat = {"chat_id": 123, "enabled": True, "allowed_senders": "all", "require_reply": False}
    kb = build_chat_settings_keyboard(chat)
    assert kb is not None
