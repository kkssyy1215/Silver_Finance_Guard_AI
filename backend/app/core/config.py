from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Silver Finance Guard AI"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


settings = Settings()

