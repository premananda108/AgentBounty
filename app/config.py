"""Application configuration using Pydantic Settings"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
import json

class Settings(BaseSettings):
    """Application settings"""

    # Auth0 - Web Application
    AUTH0_DOMAIN: str
    AUTH0_CLIENT_ID: str
    AUTH0_CLIENT_SECRET: str
    AUTH0_CALLBACK_URL: str
    AUTH0_AUDIENCE: str

    # Auth0 - M2M Application (Management API)
    AUTH0_M2M_CLIENT_ID: str
    AUTH0_M2M_CLIENT_SECRET: str

    # Session
    SECRET_KEY: str

    # AI
    GEMINI_API_KEY: str
    BRIGHT_DATA_API_KEY: str | None = None

    # Blockchain (Base Sepolia)
    BASE_RPC_URL: str = "https://sepolia.base.org"
    USDC_CONTRACT_ADDRESS: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    SERVER_WALLET_ADDRESS: str
    SERVER_PRIVATE_KEY: str

    # Database
    DATABASE_PATH: str = "/tmp/agentbounty.db"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Payment & Async Approval
    APPROVAL_THRESHOLD_USD: float = 0.002  # Require async approval for payments >= $0.002

    # Backward compatibility
    CIBA_THRESHOLD_USD: float = 0.002  # Deprecated: Use APPROVAL_THRESHOLD_USD
    ENABLE_REAL_CIBA: bool = False  # Deprecated: Email approval is always used

    # Email (for Magic Link payment approval)
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    FROM_EMAIL: str | None = None
    BASE_URL: str = "http://localhost:8000"  # Base URL for magic links
    USE_AUTH0_EMAIL: bool = True  # Use Auth0 for sending emails
    SENDGRID_API_KEY: str | None = None  # SendGrid API key (configured in Auth0)

    # MCP Service-to-Service Authentication
    MCP_SERVICE_TOKEN: str | None = None  # Secret token for MCP clients

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
