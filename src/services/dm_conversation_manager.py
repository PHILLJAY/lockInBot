"""
DM Conversation Manager for Bakushin AI - handles multi-turn conversations in private messages.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
import json
import discord
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert

from database.connection import get_db_manager
from database.models import User, DMConversation
from services.bakushin_personality import BakushinPersonality, ConversationTone
from services.natural_language_parser import NaturalLanguageParser, TaskIntent
from services.scheduling_engine import AdvancedSchedulingEngine

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Possible conversation states"""

    ONBOARDING = "onboarding"
    NAME_COLLECTION = "name_collection"
    GOAL_SETTING = "goal_setting"
    IDLE = "idle"
    TASK_CREATION = "task_creation"
    TIME_COLLECTION = "time_collection"
    CONFIRMATION = "confirmation"
    PAYMENT_PROMPT = "payment_prompt"
    TASK_MANAGEMENT = "task_management"


@dataclass
class UserConversation:
    """Represents an active conversation with a user"""

    user_id: int
    state: ConversationState
    context: Dict[str, Any]
    last_interaction: datetime
    expires_at: datetime
    pending_tasks: Optional[List[Dict]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "user_id": self.user_id,
            "state": self.state.value,
            "context": self.context,
            "last_interaction": self.last_interaction.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "pending_tasks": self.pending_tasks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserConversation":
        """Create from dictionary loaded from database"""
        return cls(
            user_id=data["user_id"],
            state=ConversationState(data["state"]),
            context=data["context"],
            last_interaction=datetime.fromisoformat(data["last_interaction"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            pending_tasks=data.get("pending_tasks"),
        )


class DMConversationManager:
    """Manages DM-based conversations for task creation"""

    def __init__(self, bot, db_manager, ai_handler):
        self.bot = bot
        self.db_manager = db_manager
        self.ai_handler = ai_handler
        self.personality = BakushinPersonality()
        self.nl_parser = NaturalLanguageParser(ai_handler)
        self.scheduling_engine = AdvancedSchedulingEngine()

        # Conversation timeout (24 hours)
        self.conversation_timeout = timedelta(hours=24)

        # Cache for active conversations
        self.active_conversations: Dict[int, UserConversation] = {}

    async def handle_dm_message(self, message: discord.Message):
        """Process incoming DM messages"""
        user_id = message.author.id
        content = message.content.strip()

        try:
            # Get or create conversation state
            conversation = await self.get_conversation(user_id)

            # Update last interaction
            conversation.last_interaction = datetime.utcnow()

            # Route based on current state
            if conversation.state == ConversationState.ONBOARDING:
                await self.handle_onboarding(message, conversation)
            elif conversation.state == ConversationState.NAME_COLLECTION:
                await self.handle_name_collection(message, conversation)
            elif conversation.state == ConversationState.GOAL_SETTING:
                await self.handle_goal_setting(message, conversation)
            elif conversation.state == ConversationState.IDLE:
                await self.handle_idle_input(message, conversation)
            elif conversation.state == ConversationState.TASK_CREATION:
                await self.handle_task_creation(message, conversation)
            elif conversation.state == ConversationState.TIME_COLLECTION:
                await self.handle_time_collection(message, conversation)
            elif conversation.state == ConversationState.CONFIRMATION:
                await self.handle_confirmation(message, conversation)
            elif conversation.state == ConversationState.PAYMENT_PROMPT:
                await self.handle_payment_response(message, conversation)

            # Save updated conversation state
            await self.save_conversation(conversation)

        except Exception as e:
            logger.error(f"Error handling DM from user {user_id}: {e}")
            await message.channel.send(
                "yo something went wrong on my end, try again in a sec 🤖"
            )

    async def get_conversation(self, user_id: int) -> UserConversation:
        """Get or create conversation state for user"""

        # Check cache first
        if user_id in self.active_conversations:
            conversation = self.active_conversations[user_id]
            if conversation.expires_at > datetime.utcnow():
                return conversation
            else:
                # Expired conversation
                del self.active_conversations[user_id]

        # Load from database
        db_manager = get_db_manager()
        async with db_manager.get_session() as session:
            # Check if conversation exists in database
            result = await session.execute(
                select(DMConversation).where(DMConversation.user_id == user_id)
            )
            db_conversation = result.scalar_one_or_none()

            if db_conversation and db_conversation.expires_at > datetime.utcnow():
                # Load existing conversation
                conversation_data = {
                    "user_id": db_conversation.user_id,
                    "state": db_conversation.state,
                    "context": db_conversation.context,
                    "last_interaction": db_conversation.last_interaction.isoformat(),
                    "expires_at": db_conversation.expires_at.isoformat(),
                    "pending_tasks": db_conversation.pending_tasks,
                }
                conversation = UserConversation.from_dict(conversation_data)
            else:
                # Create new conversation
                conversation = UserConversation(
                    user_id=user_id,
                    state=ConversationState.ONBOARDING,
                    context={},
                    last_interaction=datetime.utcnow(),
                    expires_at=datetime.utcnow() + self.conversation_timeout,
                )

        # Cache the conversation
        self.active_conversations[user_id] = conversation
        return conversation

    async def handle_onboarding(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle initial onboarding flow"""

        # Check if user is already registered
        db_manager = get_db_manager()
        async with db_manager.get_session() as session:
            stmt = select(User).where(User.id == message.author.id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                # Existing user - skip to goal setting
                conversation.context["name"] = user.username
                conversation.context["returning_user"] = True
                conversation.state = ConversationState.GOAL_SETTING

                response = self.personality.generate_response(
                    context=conversation.context, tone=ConversationTone.GREETING
                )
            else:
                # New user - start name collection
                conversation.state = ConversationState.NAME_COLLECTION
                response = self.personality.generate_response(
                    context={"is_first_time": True}, tone=ConversationTone.GREETING
                )

        await message.channel.send(response)

    async def handle_name_collection(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle name collection from new users"""
        name = message.content.strip()

        # Validate name
        if len(name) < 2 or len(name) > 50 or not name.replace(" ", "").isalnum():
            response = "bruh that's not a name\ntry again with something that's actually a name lol"
            await message.channel.send(response)
            return

        # Store name and move to goal setting
        conversation.context["name"] = name
        conversation.context["name_is_basic"] = name.lower() in [
            "john",
            "mike",
            "alex",
            "chris",
            "sam",
        ]
        conversation.state = ConversationState.GOAL_SETTING

        response = self.personality.generate_response(
            context=conversation.context, tone=ConversationTone.GOAL_SETTING
        )

        await message.channel.send(response)

    async def handle_goal_setting(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle goal setting conversation"""
        goal_text = message.content.strip()

        # Check if this looks like a task creation request
        if await self.is_task_creation_request(goal_text):
            conversation.context["initial_goal"] = goal_text
            conversation.state = ConversationState.TASK_CREATION
            await self.handle_task_creation(message, conversation)
        else:
            # General goal discussion - ask for more specific task
            conversation.context["general_goal"] = goal_text

            response = (
                "ok i see the vision but we need to get specific\n\n"
                "vague goals = vague results\n\n"
                "tell me something concrete you want to do regularly\n"
                'like "work out 3 times a week" or "read every night"'
            )

            await message.channel.send(response)

    async def handle_idle_input(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle input when user is in idle state"""
        content = message.content.strip()

        # Check if it's a task creation request
        if await self.is_task_creation_request(content):
            conversation.state = ConversationState.TASK_CREATION
            await self.handle_task_creation(message, conversation)
        else:
            # Handle other types of requests (list tasks, help, etc.)
            await self.handle_general_request(message, conversation)

    async def handle_task_creation(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle natural language task creation"""
        content = message.content.strip()

        # Parse the natural language input
        try:
            parsed_intent = await self.nl_parser.parse_task_intent(content)
            conversation.context["parsed_intent"] = asdict(parsed_intent)

            if parsed_intent.confidence > 0.7:
                # High confidence - check what information is missing
                missing_info = parsed_intent.missing_info

                if missing_info and "time" in missing_info:
                    await self.ask_for_time(
                        message.channel, parsed_intent, conversation
                    )
                    conversation.state = ConversationState.TIME_COLLECTION
                else:
                    await self.generate_and_confirm_tasks(message.channel, conversation)
            else:
                # Low confidence - ask for clarification
                await self.send_clarification_request(message.channel, content)

        except Exception as e:
            logger.error(f"Error parsing task intent: {e}")
            await message.channel.send(
                "hmm couldn't figure that out, try being more specific?\n"
                'like "work out 3 times a week" or "read daily at 9pm"'
            )

    async def handle_time_collection(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle time collection for task creation"""
        time_text = message.content.strip()

        # Parse time expression
        parsed_time = await self.nl_parser.parse_time_expression(time_text)

        if parsed_time:
            # Update the parsed intent with time information
            if "parsed_intent" in conversation.context:
                conversation.context["parsed_intent"]["time_preference"] = time_text
                conversation.context["parsed_intent"]["parsed_time"] = (
                    parsed_time.strftime("%H:%M")
                )
                conversation.context["parsed_intent"]["missing_info"] = [
                    info
                    for info in conversation.context["parsed_intent"]["missing_info"]
                    if info != "time"
                ]

            # Generate and confirm tasks
            await self.generate_and_confirm_tasks(message.channel, conversation)
        else:
            # Invalid time - ask again
            response = (
                "hmm that doesn't look like a time to me\n\n"
                "try something like:\n"
                "• 7:30 AM\n"
                "• morning\n"
                "• after work\n"
                "• 6 PM"
            )
            await message.channel.send(response)

    async def handle_confirmation(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle task confirmation"""
        response = message.content.strip().lower()

        if response in ["yes", "y", "yeah", "yep", "sure", "ok"]:
            # Create the tasks
            await self.create_confirmed_tasks(message, conversation)
        elif response in ["no", "n", "nah", "nope"]:
            # Go back to task creation
            conversation.state = ConversationState.TASK_CREATION
            await message.channel.send(
                "no worries, let's adjust it\nwhat would you like to change?"
            )
        else:
            # Ask for clear yes/no
            await message.channel.send(
                "just need a yes or no fam\ndoes this schedule work for you?"
            )

    async def handle_payment_response(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle payment prompt response"""
        response = message.content.strip().lower()

        if response in ["yes", "y", "yeah", "yep", "sure", "ok", "down"]:
            # User agreed to payment - would integrate with payment system
            await message.channel.send(
                "bet! payment integration coming soon 💳\n\n"
                "for now your tasks are set up and ill start sending reminders\n"
                "time to lock in and show me what you got 🔥"
            )
            conversation.state = ConversationState.IDLE
        elif response in ["no", "n", "nah", "nope", "not now"]:
            # User declined payment
            await message.channel.send(
                "no worries, i get it\n\n"
                "your tasks are still set up for now\n"
                "but just so you know, the free trial ends soon\n\n"
                "hit me up when you're ready to get serious about your goals 💪"
            )
            conversation.state = ConversationState.IDLE
        else:
            # Ask for clear response
            await message.channel.send(
                "so... you down for $5/month or nah?\njust need a yes or no"
            )

    async def is_task_creation_request(self, text: str) -> bool:
        """Determine if text is a task creation request"""
        task_indicators = [
            "want to",
            "need to",
            "should",
            "goal",
            "habit",
            "daily",
            "every",
            "times",
            "work out",
            "exercise",
            "read",
            "meditate",
            "study",
            "practice",
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in task_indicators)

    async def ask_for_time(
        self, channel, parsed_intent: TaskIntent, conversation: UserConversation
    ):
        """Ask user for time preference"""

        # Determine goal type for personalized response
        goal_type = self.determine_goal_type(parsed_intent.task_name)
        conversation.context["goal_type"] = goal_type

        response = self.personality.generate_response(
            context=conversation.context, tone=ConversationTone.TASK_CREATION
        )

        await channel.send(response)

    async def generate_and_confirm_tasks(self, channel, conversation: UserConversation):
        """Generate task schedule and ask for confirmation"""

        if "parsed_intent" not in conversation.context:
            await channel.send("something went wrong, let's start over")
            conversation.state = ConversationState.IDLE
            return

        intent_data = conversation.context["parsed_intent"]

        # Generate schedule using scheduling engine
        try:
            # Convert intent data back to TaskIntent object
            parsed_intent = TaskIntent(
                task_name=intent_data["task_name"],
                frequency_type=intent_data["frequency_type"],
                frequency_value=intent_data.get("frequency_value"),
                time_preference=intent_data.get("time_preference"),
                description=intent_data.get("description"),
                confidence=intent_data["confidence"],
                missing_info=intent_data.get("missing_info", []),
            )

            # Generate schedule
            schedule_pattern = await self.nl_parser.create_schedule_pattern(
                parsed_intent
            )
            generated_tasks = await self.scheduling_engine.generate_schedule(
                schedule_pattern, parsed_intent.task_name, parsed_intent.description
            )

            # Store generated tasks
            conversation.pending_tasks = [asdict(task) for task in generated_tasks]

            # Create confirmation message
            confirmation_message = self.create_task_preview(
                parsed_intent, generated_tasks
            )

            await channel.send(confirmation_message)
            conversation.state = ConversationState.CONFIRMATION

        except Exception as e:
            logger.error(f"Error generating schedule: {e}")
            await channel.send(
                "oof had trouble setting that up\n"
                "can you try describing it differently?"
            )
            conversation.state = ConversationState.TASK_CREATION

    def create_task_preview(self, intent: TaskIntent, generated_tasks: List) -> str:
        """Create a preview of generated tasks for confirmation"""

        preview_lines = [f"bet! so here's what im setting up for you:\n"]

        # Add task emoji based on type
        emoji = self.get_task_emoji(intent.task_name)
        preview_lines.append(f"{emoji} {intent.task_name.title()} Schedule:")

        # List each task
        for task in generated_tasks:
            if task.days_of_week:
                days = [
                    [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    ][day]
                    for day in task.days_of_week
                ]
                for day in days:
                    preview_lines.append(
                        f"• {day} at {task.reminder_time.strftime('%H:%M')}"
                    )
            else:
                # Interval-based task
                if task.interval_days == 2:
                    preview_lines.append(
                        f"• Every other day at {task.reminder_time.strftime('%H:%M')}"
                    )
                else:
                    preview_lines.append(
                        f"• Every {task.interval_days} days at {task.reminder_time.strftime('%H:%M')}"
                    )

        preview_lines.extend(
            [
                "\nill hit you up each time to make sure you actually show up",
                "and not just snooze your way to failure like most people lol\n",
                "this look good? (yes/no)",
            ]
        )

        return "\n".join(preview_lines)

    def get_task_emoji(self, task_name: str) -> str:
        """Get appropriate emoji for task type"""
        task_lower = task_name.lower()

        if any(word in task_lower for word in ["work", "exercise", "gym", "lift"]):
            return "🏋️"
        elif any(word in task_lower for word in ["read", "book", "study"]):
            return "📚"
        elif any(word in task_lower for word in ["meditate", "mindful"]):
            return "🧘"
        elif any(word in task_lower for word in ["run", "jog", "cardio"]):
            return "🏃"
        elif any(word in task_lower for word in ["write", "journal"]):
            return "✍️"
        else:
            return "🎯"

    def determine_goal_type(self, task_name: str) -> str:
        """Determine the type of goal for personalized responses"""
        task_lower = task_name.lower()

        if any(
            word in task_lower
            for word in ["work", "exercise", "gym", "lift", "run", "cardio"]
        ):
            return "fitness"
        elif any(word in task_lower for word in ["read", "book", "study"]):
            return "reading"
        elif any(word in task_lower for word in ["meditate", "mindful"]):
            return "mindfulness"
        elif any(word in task_lower for word in ["write", "journal"]):
            return "writing"
        else:
            return "general"

    async def create_confirmed_tasks(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Create tasks in database after user confirmation"""

        if not conversation.pending_tasks:
            await message.channel.send("something went wrong, no tasks to create")
            return

        try:
            # Import here to avoid circular imports
            from database.models import Task, Streak

            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                # Get or create user
                stmt = select(User).where(User.id == message.author.id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    # Create new user
                    user = User(
                        id=message.author.id,
                        username=conversation.context.get(
                            "name", message.author.display_name
                        ),
                        timezone="UTC",  # Default timezone
                        created_at=datetime.utcnow(),
                        last_active=datetime.utcnow(),
                    )
                    session.add(user)
                    await session.flush()  # Get user ID

                # Create a single recurring task instead of multiple individual tasks
                created_tasks = []

                # Get the first task data to use as the basis for our recurring task
                first_task_data = conversation.pending_tasks[0]

                # Determine the base task name (without day-specific suffixes)
                base_task_name = first_task_data["name"]
                if " (" in base_task_name and base_task_name.endswith(")"):
                    # Remove day-specific suffix like " (Monday)"
                    base_task_name = base_task_name[: base_task_name.rfind(" (")]

                # Collect all days of week from all tasks
                all_days_of_week = set()
                for task_data in conversation.pending_tasks:
                    if task_data["days_of_week"]:
                        all_days_of_week.update(task_data["days_of_week"])

                # Sort the days for consistent ordering
                all_days_of_week = sorted(list(all_days_of_week))

                # Determine recurrence pattern
                if all_days_of_week:
                    # Weekly recurring task
                    recurrence_pattern = "weekly"
                    # Convert list of integers to comma-separated string
                    days_of_week_str = ",".join(str(day) for day in all_days_of_week)
                else:
                    # Check if any task has interval_days
                    interval_days = None
                    for task_data in conversation.pending_tasks:
                        if task_data.get("interval_days"):
                            interval_days = task_data["interval_days"]
                            break

                    if interval_days:
                        # Interval-based recurring task
                        recurrence_pattern = (
                            "daily"  # Using daily as base pattern for intervals
                        )
                        days_of_week_str = None
                    else:
                        # Daily recurring task
                        recurrence_pattern = "daily"
                        days_of_week_str = None

                # Create a single recurring task
                new_task = Task(
                    user_id=message.author.id,
                    name=base_task_name,
                    description=first_task_data.get("description"),
                    reminder_time=first_task_data["reminder_time"],
                    timezone=user.timezone,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    generation_method="natural_language",
                    is_recurring=True,
                    recurrence_pattern=recurrence_pattern,
                    recurrence_interval=interval_days if interval_days else 1,
                    days_of_week=days_of_week_str,
                )
                session.add(new_task)
                created_tasks.append(new_task)

                await session.commit()

                # Refresh tasks to get IDs
                for task in created_tasks:
                    await session.refresh(task)

                    # Create initial streak record
                    initial_streak = Streak(
                        user_id=message.author.id,
                        task_id=task.id,
                        current_streak=0,
                        longest_streak=0,
                        last_completion_date=None,
                    )
                    session.add(initial_streak)

                await session.commit()

                # Schedule the tasks with the bot's scheduler
                scheduler = self.bot.get_scheduler()
                for task in created_tasks:
                    await scheduler.add_task_schedule(task)

                # Send success message and payment prompt
                success_message = self.personality.generate_response(
                    context=conversation.context, tone=ConversationTone.PAYMENT_PROMPT
                )

                await message.channel.send(success_message)
                conversation.state = ConversationState.PAYMENT_PROMPT

        except Exception as e:
            logger.error(f"Error creating tasks: {e}")
            await message.channel.send(
                "oof something went wrong creating your tasks\ntry again in a bit?"
            )

    async def send_clarification_request(self, channel, original_input: str):
        """Send clarification request for unclear input"""
        response = (
            "hmm not sure what you mean by that\n\n"
            "try being more specific like:\n"
            '• "work out 3 times a week"\n'
            '• "read every night at 9pm"\n'
            '• "meditate daily in the morning"\n\n'
            "what did you have in mind?"
        )
        await channel.send(response)

    async def handle_general_request(
        self, message: discord.Message, conversation: UserConversation
    ):
        """Handle general requests like help, list tasks, etc."""
        content = message.content.lower().strip()

        if any(word in content for word in ["help", "commands", "what can you do"]):
            response = (
                "yo here's what i can help with:\n\n"
                "• just tell me your goals in plain english\n"
                '• "work out 3 times a week"\n'
                '• "read every night"\n'
                '• "meditate daily"\n\n'
                "ill figure out the schedule and keep you accountable 💪"
            )
        elif any(
            word in content for word in ["tasks", "list", "show", "what do i have"]
        ):
            # This would integrate with existing task listing functionality
            response = (
                "lemme check what you got going...\n"
                "use `/list_tasks` in a server to see everything\n"
                "or just tell me about new habits you want to build!"
            )
        else:
            response = (
                "not sure what you're asking for\n"
                "just tell me about habits you want to build\n"
                'or say "help" if you\'re lost'
            )

        await message.channel.send(response)

    async def save_conversation(self, conversation: UserConversation):
        """Save conversation state to database"""
        try:
            # Import here to avoid circular imports
            from database.models import DMConversation

            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                # Use upsert to handle both insert and update
                stmt = insert(DMConversation).values(
                    user_id=conversation.user_id,
                    state=conversation.state.value,
                    context=conversation.context,
                    last_interaction=conversation.last_interaction,
                    expires_at=conversation.expires_at,
                    pending_tasks=conversation.pending_tasks,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["user_id"],
                    set_=dict(
                        state=stmt.excluded.state,
                        context=stmt.excluded.context,
                        last_interaction=stmt.excluded.last_interaction,
                        expires_at=stmt.excluded.expires_at,
                        pending_tasks=stmt.excluded.pending_tasks,
                    ),
                )
                await session.execute(stmt)
                await session.commit()

        except Exception as e:
            logger.error(f"Error saving conversation state: {e}")

    async def cleanup_expired_conversations(self):
        """Clean up expired conversations from database and cache"""
        try:
            # Import here to avoid circular imports
            from database.models import DMConversation

            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                # Delete expired conversations from database
                await session.execute(
                    DMConversation.__table__.delete().where(
                        DMConversation.expires_at < datetime.utcnow()
                    )
                )
                await session.commit()

            # Clean up cache
            expired_users = [
                user_id
                for user_id, conv in self.active_conversations.items()
                if conv.expires_at < datetime.utcnow()
            ]
            for user_id in expired_users:
                del self.active_conversations[user_id]

        except Exception as e:
            logger.error(f"Error cleaning up expired conversations: {e}")
