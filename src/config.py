"""
Configuration management for the Discord Task Reminder Bot.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration class for the Discord Task Reminder Bot."""

    # Required fields (no defaults)
    discord_token: str
    openai_api_key: str
    database_url: str

    # Optional Discord Configuration
    discord_guild_id: Optional[str] = None

    # OpenAI Configuration
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 150

    # Bot Configuration
    environment: str = "development"
    log_level: str = "INFO"
    command_prefix: str = "/"
    max_image_size_mb: int = 10
    reminder_channel_name: str = "task-reminders"

    # Timezone Configuration
    default_timezone: str = "UTC"

    # Cost Management
    daily_api_limit_per_user: int = 20
    monthly_budget_alert_usd: float = 50.0

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            # Discord
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            discord_guild_id=os.getenv("DISCORD_GUILD_ID"),
            # OpenAI
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "150")),
            # Database
            database_url=os.getenv("DATABASE_URL", ""),
            # Bot
            environment=os.getenv("ENVIRONMENT", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            command_prefix=os.getenv("COMMAND_PREFIX", "/"),
            max_image_size_mb=int(os.getenv("MAX_IMAGE_SIZE_MB", "10")),
            reminder_channel_name=os.getenv("REMINDER_CHANNEL_NAME", "task-reminders"),
            # Timezone
            default_timezone=os.getenv("DEFAULT_TIMEZONE", "UTC"),
            # Cost Management
            daily_api_limit_per_user=int(os.getenv("DAILY_API_LIMIT_PER_USER", "20")),
            monthly_budget_alert_usd=float(
                os.getenv("MONTHLY_BUDGET_ALERT_USD", "50.0")
            ),
        )

    def validate(self) -> None:
        """Validate configuration values."""
        errors = []

        if not self.discord_token:
            errors.append("DISCORD_TOKEN is required")

        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")

        if not self.database_url:
            errors.append("DATABASE_URL is required")

        if self.openai_max_tokens < 50 or self.openai_max_tokens > 4000:
            errors.append("OPENAI_MAX_TOKENS must be between 50 and 4000")

        if self.max_image_size_mb < 1 or self.max_image_size_mb > 25:
            errors.append("MAX_IMAGE_SIZE_MB must be between 1 and 25")

        if self.daily_api_limit_per_user < 1:
            errors.append("DAILY_API_LIMIT_PER_USER must be at least 1")

        if self.log_level.upper() not in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ]:
            errors.append(
                "LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )

        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    def __repr__(self) -> str:
        """String representation of config (without sensitive data)."""
        return (
            f"Config("
            f"environment={self.environment}, "
            f"log_level={self.log_level}, "
            f"openai_model={self.openai_model}, "
            f"max_tokens={self.openai_max_tokens}, "
            f"max_image_size={self.max_image_size_mb}MB"
            f")"
        )
