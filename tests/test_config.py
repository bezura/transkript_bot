from transkript_bot.config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.default_language == "auto"
    assert s.idle_shutdown_minutes == 5
    assert s.allowed_senders_default == "whitelist"


def test_settings_bot_api_base_url():
    s = Settings(_env_file=None)
    assert s.bot_api_base_url is None
    custom = Settings(_env_file=None, bot_api_base_url="http://localhost:8081")
    assert custom.bot_api_base_url == "http://localhost:8081"
