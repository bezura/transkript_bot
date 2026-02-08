from transkript_bot.config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.default_language == "auto"
    assert s.idle_shutdown_minutes == 5
    assert s.allowed_senders_default == "whitelist"
