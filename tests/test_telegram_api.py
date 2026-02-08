from transkript_bot.config import Settings
from transkript_bot.services.telegram_api import build_api_server


def test_build_api_server_default():
    settings = Settings(_env_file=None)
    server = build_api_server(settings)
    assert server.base.startswith("https://api.telegram.org/")


def test_build_api_server_custom():
    settings = Settings(_env_file=None, bot_api_base_url="http://localhost:8081")
    server = build_api_server(settings)
    assert server.base.startswith("http://localhost:8081/")
    assert server.is_local is True
