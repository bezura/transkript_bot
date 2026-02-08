from transkript_bot.services.keyboard import (
    build_chat_settings_keyboard,
    build_request_action_keyboard,
)


def test_chat_settings_keyboard():
    chat = {"chat_id": 123, "enabled": True, "allowed_senders": "all", "require_reply": False}
    kb = build_chat_settings_keyboard(chat)
    assert kb is not None


def test_request_action_keyboard():
    kb = build_request_action_keyboard(kind="user", request_id=7)
    buttons = [button for row in kb.inline_keyboard for button in row]
    callback_data = {button.callback_data for button in buttons}
    assert "admin:req:user:approve:7" in callback_data
    assert "admin:req:user:deny:7" in callback_data
