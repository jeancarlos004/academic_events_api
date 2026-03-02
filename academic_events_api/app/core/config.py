from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "supersecretkey_change_in_production_min32chars"
    REFRESH_SECRET_KEY: str = "refresh_supersecretkey_change_in_production_min32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = "sqlite:///./academic_events.db"

    class Config:
        env_file = ".env"


settings = Settings()
