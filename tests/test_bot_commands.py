from transkript_bot.services.commands import build_command_scopes


def test_command_scopes_include_admins():
    scopes = build_command_scopes(root_admin_ids={1})
    assert "all_private_chats" in scopes
    assert "all_chat_administrators" in scopes
