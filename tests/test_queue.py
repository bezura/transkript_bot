from transkript_bot.services.queue import estimate_eta


def test_eta_from_history():
    durations = [60, 120, 90]
    assert estimate_eta(durations, position=3) == 180
