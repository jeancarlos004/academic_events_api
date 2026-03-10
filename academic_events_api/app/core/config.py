from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "supersecretkey_change_in_production_min32chars"
    REFRESH_SECRET_KEY: str = "refresh_supersecretkey_change_in_production_min32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = "sqlite:///./academic_events.db"
    GROQ_API_KEY: str | None = None
    COLAB_API: str | None = None
    COLAB_CHAT_URL: str | None = None
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    TINYLLAMA_MODEL: str = "tinyllama"

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
