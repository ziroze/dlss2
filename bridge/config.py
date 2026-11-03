from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")
    bridge_admin_token: SecretStr = SecretStr("change-me")
    bridge_secret: SecretStr = SecretStr("change-me-too")
    bridge_database: str = "./data/bridge.sqlite3"
    bridge_enrollment_ttl_minutes: int = 15
    bridge_job_lease_seconds: int = 60
    bridge_agent_poll_seconds: int = 5
    bridge_cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [v.strip() for v in self.bridge_cors_origins.split(",") if v.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
