from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "mysql+pymysql://root:@localhost:3306/db_vivienda"
    SECRET_KEY: str = "dev-secret-change-me"
    ACCESS_TOKEN_MINUTES: int = 60
    RESET_TOKEN_MINUTES: int = 30
    FRONTEND_URL: str = "http://localhost:4200"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@convive.local"


settings = Settings()
