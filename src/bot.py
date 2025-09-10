"""
Core Discord bot implementation for the Task Reminder Bot.
"""

import logging
import asyncio
from typing import Optional, TYPE_CHECKING
import discord
from discord.ext import commands

if TYPE_CHECKING:
    from services.dm_conversation_manager import DMConversationManager

from config import Config
from database.connection import DatabaseManager, set_db_manager
from services.ai_handler import AIHandler
from services.scheduler import TaskScheduler
from services.streak_manager import StreakManager
from commands.user_commands import UserCommands
from commands.task_commands import TaskCommands
from commands.completion_commands import CompletionCommands

logger = logging.getLogger(__name__)


class TaskReminderBot(commands.Bot):
    """Main Discord bot class for task reminders and streak tracking."""

    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize the bot with configuration and database manager."""

        # Set up bot intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = True
        intents.dm_reactions = True

        # Initialize bot
        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents,
            help_command=None,  # We'll create a custom help command
            case_insensitive=True,
        )

        self.config = config
        self.db_manager = db_manager

        # Set global database manager
        set_db_manager(db_manager)

        # Initialize services
        self.ai_handler: Optional[AIHandler] = None
        self.scheduler: Optional[TaskScheduler] = None
        self.streak_manager: Optional[StreakManager] = None
        self.dm_conversation_manager: Optional["DMConversationManager"] = None

        # Bot state
        self.is_ready = False

    async def setup_hook(self) -> None:
        """Set up the bot after login but before ready event."""
        logger.info("Setting up bot services...")

        try:
            # Initialize AI handler
            self.ai_handler = AIHandler(self.config)
            logger.info("AI handler initialized")

            # Initialize streak manager
            self.streak_manager = StreakManager(self.db_manager)
            logger.info("Streak manager initialized")

            # Initialize scheduler
            self.scheduler = TaskScheduler(self, self.db_manager, self.ai_handler)
            await self.scheduler.start()
            logger.info("Task scheduler initialized and started")

            # Initialize DM conversation manager
            from services.dm_conversation_manager import DMConversationManager

            self.dm_conversation_manager = DMConversationManager(
                self, self.db_manager, self.ai_handler
            )
            logger.info("DM conversation manager initialized")

            # Add command cogs
            await self.add_cog(UserCommands(self))
            await self.add_cog(TaskCommands(self))
            await self.add_cog(CompletionCommands(self))
            logger.info("Command cogs loaded")

            # Sync slash commands
            if self.config.discord_guild_id:
                guild = discord.Object(id=int(self.config.discord_guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(
                    f"Slash commands synced to guild {self.config.discord_guild_id}"
                )
            else:
                await self.tree.sync()
                logger.info("Slash commands synced globally")

        except Exception as e:
            logger.error(f"Failed to set up bot services: {e}")
            raise

    async def on_ready(self) -> None:
        """Called when the bot is ready and connected to Discord."""
        logger.info(f"Bot is ready! Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching, name="your daily tasks 📋"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        self.is_ready = True
        logger.info("Bot is fully operational")

    async def on_message(self, message):
        """Handle all messages including DMs"""
        if message.author.bot:
            return

        # Check if it's a DM
        if isinstance(message.channel, discord.DMChannel):
            await self.handle_dm_conversation(message)
        else:
            # Process commands for server messages
            await self.process_commands(message)

    async def handle_dm_conversation(self, message: discord.Message):
        """Handle DM conversations for natural language task creation"""
        if not self.dm_conversation_manager:
            await message.channel.send(
                "yo my brain isn't fully loaded yet, try again in a sec 🤖"
            )
            return

        try:
            await self.dm_conversation_manager.handle_dm_message(message)
        except Exception as e:
            logger.error(f"Error handling DM conversation: {e}")
            await message.channel.send(
                "oof something went wrong on my end, try again in a bit 🤖"
            )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        # Send welcome message to the first available text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="🎯 Task Reminder Bot",
                    description=(
                        "Thanks for adding me to your server! I help you stay on track with daily tasks.\n\n"
                        "**Get Started:**\n"
                        "• Use `/register` to set up your account\n"
                        "• Use `/create_task` to add your first task\n"
                        "• Use `/help` to see all available commands\n\n"
                        "I'll send daily reminders and help you maintain streaks! 💪"
                    ),
                    color=0x00FF00,
                )
                embed.set_footer(text="Use /help for more information")

                try:
                    await channel.send(embed=embed)
                    break
                except discord.Forbidden:
                    continue

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument provided: {error}")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ Command on cooldown. Try again in {error.retry_after:.1f} seconds."
            )

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")

        else:
            logger.error(f"Unhandled command error: {error}", exc_info=error)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        """Handle slash command errors."""
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏰ Command on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True,
            )

        elif isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=True
            )

        else:
            logger.error(f"Unhandled app command error: {error}", exc_info=error)

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An unexpected error occurred. Please try again later.",
                    ephemeral=True,
                )

    async def close(self) -> None:
        """Clean shutdown of the bot."""
        logger.info("Shutting down bot...")

        # Stop scheduler
        if self.scheduler:
            await self.scheduler.stop()

        # Close database connection
        if self.db_manager:
            await self.db_manager.close()

        # Close bot connection
        await super().close()
        logger.info("Bot shutdown complete")

    def get_ai_handler(self) -> AIHandler:
        """Get the AI handler instance."""
        if not self.ai_handler:
            raise RuntimeError("AI handler not initialized")
        return self.ai_handler

    def get_scheduler(self) -> TaskScheduler:
        """Get the task scheduler instance."""
        if not self.scheduler:
            raise RuntimeError("Task scheduler not initialized")
        return self.scheduler

    def get_streak_manager(self) -> StreakManager:
        """Get the streak manager instance."""
        if not self.streak_manager:
            raise RuntimeError("Streak manager not initialized")
        return self.streak_manager

    def get_dm_conversation_manager(self) -> "DMConversationManager":
        """Get the DM conversation manager instance."""
        if not self.dm_conversation_manager:
            raise RuntimeError("DM conversation manager not initialized")
        return self.dm_conversation_manager
