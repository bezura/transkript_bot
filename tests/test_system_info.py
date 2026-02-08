from transkript_bot.services.system_info import get_system_info


def test_system_info_keys():
    info = get_system_info()
    assert "os" in info
    assert "python" in info
    assert "cpu_count" in info
    assert "memory_total_gb" in info
