from transkript_bot.services.menu import MenuRole, build_help_text


def test_help_text_for_user():
    text = build_help_text(role=MenuRole.USER, in_private=True)
    assert "/admin" not in text
    assert "/menu" in text


def test_help_text_for_root_admin():
    text = build_help_text(role=MenuRole.ROOT_ADMIN, in_private=True)
    assert "/admin" in text
