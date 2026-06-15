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

    # Transactional email (welcome + password reset). Two transports, both
    # optional: RESEND_API_KEY uses Resend's HTTP API (port 443 — preferred,
    # since many hosts including HF Spaces block outbound SMTP ports); the SMTP
    # fields are a fallback for any other provider. With nothing configured the
    # app skips sending entirely (logged at info), so tests never touch the net.
    resend_api_key: str = ""
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
        """True when a transport is available: Resend HTTP API, or full SMTP."""
        return bool(self.resend_api_key) or bool(
            self.smtp_host and self.smtp_user and self.smtp_password
        )


settings = Settings()
