"""Application settings loaded from environment variables / .env (spec §13)."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./lbo_screener.db"
    jwt_secret: str = "dev-secret-change-me"
    data_provider: Literal["auto", "mock", "live", "yahoo"] = "auto"
    sec_edgar_user_agent: str = ""
    fmp_api_key: str = ""
    polygon_api_key: str = ""
    alphavantage_api_key: str = ""
    tiingo_api_key: str = ""
    cors_origins: str = "http://localhost:3000"

    # SMTP / transactional email (welcome + password reset). All optional:
    # with host/user/password blank the app skips sending entirely (logged at
    # info), so tests and local dev never touch the network.
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Investment Intelligence <contact@nikolasdionsavio.com>"
    # Base URL of the frontend, used to build the password-reset link.
    frontend_url: str = "https://nikolasproject.com"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def email_configured(self) -> bool:
        """True only when host, user and password are all set."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)


settings = Settings()
