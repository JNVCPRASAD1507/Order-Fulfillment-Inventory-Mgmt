
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Order Fulfillment & Inventory Management Platform"
    environment: str = "development"
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    algorithm: str = "HS256"
    
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
