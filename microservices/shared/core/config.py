#!/usr/bin/env python3
"""
Shared Configuration Management for Microservices
This provides a flexible configuration that works across all microservices
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    """Shared application settings with validation - all fields optional with defaults"""

    # Application
    APP_NAME: str = "DevOps Ticket Management System"
    APP_VERSION: str = "3.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-minimum-32-characters")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://devops_user:devops_password_change_this@postgres:5432/devops_tickets"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 50

    # Redmine (optional for services that don't need it)
    REDMINE_BASE_URL: str = os.getenv("REDMINE_BASE_URL", "https://redmine.example.com")
    REDMINE_API_KEY: str = os.getenv("REDMINE_API_KEY", "")
    DEVOPS_PROJECT_ID: int = 1
    DEVOPS_TEAM_GROUP_ID: int = 6

    # LLM (optional for services that don't need it)
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://ollama:11434")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama2")
    LLM_TIMEOUT: int = 120
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.7
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "false").lower() == "true"

    # Notifications (optional)
    GOOGLE_CHAT_WEBHOOK: Optional[str] = os.getenv("GOOGLE_CHAT_WEBHOOK")
    GOOGLE_CHAT_ENABLED: bool = os.getenv("GOOGLE_CHAT_ENABLED", "false").lower() == "true"
    SLACK_WEBHOOK: Optional[str] = os.getenv("SLACK_WEBHOOK")
    SLACK_ENABLED: bool = False

    # Scheduler (optional - only for services that need it)
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    TICKET_PROCESSING_INTERVAL: int = 2  # minutes
    SLA_CHECK_INTERVAL: int = 1  # minutes
    ANALYTICS_UPDATE_INTERVAL: int = 60  # minutes
    REDMINE_STATUS_SYNC_INTERVAL: int = 5  # minutes

    # ML Models (optional)
    ML_MODELS_PATH: str = "./models"
    ML_TRAINING_ENABLED: bool = True
    ML_MIN_TRAINING_SAMPLES: int = 50

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production-minimum-32-characters")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://10.0.2.121:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # Monitoring (optional)
    PROMETHEUS_ENABLED: bool = False
    SENTRY_DSN: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Public base URL for external callbacks
    PUBLIC_API_BASE_URL: Optional[str] = os.getenv("PUBLIC_API_BASE_URL")

    # Business hours configuration
    BUSINESS_TIMEZONE: str = "Asia/Kolkata"
    BUSINESS_HOURS_START: int = 9   # 9 AM local time
    BUSINESS_HOURS_END: int = 18    # 6 PM local time
    BUSINESS_DAYS: List[int] = [0, 1, 2, 3, 4]  # Monday-Friday

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields for service-specific config


# Global settings instance - can be imported by services
settings = Settings()
