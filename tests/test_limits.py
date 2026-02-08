from transkript_bot.services.limits import MAX_CLOUD_FILE_SIZE, is_cloud_file_too_large


def test_cloud_file_limit():
    assert not is_cloud_file_too_large(MAX_CLOUD_FILE_SIZE)
    assert is_cloud_file_too_large(MAX_CLOUD_FILE_SIZE + 1)
