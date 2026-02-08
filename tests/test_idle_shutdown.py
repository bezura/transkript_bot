from transkript_bot.services.idle_shutdown import should_shutdown


def test_should_shutdown():
    assert should_shutdown(last_activity_sec=400, idle_limit_sec=300) is True
