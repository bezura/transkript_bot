import inspect

from transkript_bot.routers import admin, media


def _params(func):
    return set(inspect.signature(func).parameters)


def test_admin_handlers_use_app_state():
    for func in (
        admin.admin_toggle,
        admin.allow_user,
        admin.deny_user,
        admin.stats,
        admin.system_info_cmd,
    ):
        params = _params(func)
        assert "state" not in params
        assert "app_state" in params


def test_media_handler_uses_app_state():
    params = _params(media.handle_media)
    assert "state" not in params
    assert "app_state" in params
