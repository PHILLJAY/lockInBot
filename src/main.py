#!/usr/bin/env python3
"""
Discord Task Reminder Bot - Main Entry Point

A GPT-powered Discord bot that provides personalized daily task reminders
with streak tracking and AI-powered image verification.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from bot import TaskReminderBot
from database.connection import DatabaseManager


async def main():
    """Main entry point for the Discord Task Reminder Bot."""

    # Load configuration
    try:
        config = Config.from_env()
        config.validate()
    except Exception as e:
        logging.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("bot.log")
            if config.environment == "production"
            else logging.NullHandler(),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Discord Task Reminder Bot...")

    # Initialize database
    try:
        db_manager = DatabaseManager(config.database_url)
        await db_manager.initialize()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Initialize and start bot
    try:
        bot = TaskReminderBot(config, db_manager)
        await bot.start(config.discord_token)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Bot encountered an error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await db_manager.close()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot shutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
