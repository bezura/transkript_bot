from transkript_bot.services.commands import parse_user_id


def test_parse_user_id():
    assert parse_user_id("/allow 123") == 123
    assert parse_user_id("/deny 999") == 999
