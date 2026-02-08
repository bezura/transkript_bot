from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str | None = None
    root_admin_ids: list[int] = []
    hf_token: str | None = None
    storage_path: str = "./data/bot.db"
    media_dir: str = "./data/media"
    idle_shutdown_minutes: int = 5
    default_language: str = "auto"
    allowed_senders_default: str = "whitelist"
    backend_force: str | None = None
    whisperx_cmd: str = "whisperx"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
