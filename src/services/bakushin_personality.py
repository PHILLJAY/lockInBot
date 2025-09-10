"""
Bakushin Personality Engine - manages the casual 20-something horse personality.
"""

import random
from enum import Enum
from typing import Dict, Any, List
from datetime import datetime


class ConversationTone(Enum):
    """Different conversation tones for Bakushin"""

    GREETING = "greeting"
    GOAL_SETTING = "goal_setting"
    TASK_CREATION = "task_creation"
    MOTIVATION = "motivation"
    REALITY_CHECK = "reality_check"
    CELEBRATION = "celebration"
    PAYMENT_PROMPT = "payment_prompt"
    CLARIFICATION = "clarification"


class BakushinPersonality:
    """Manages Bakushin's personality and conversation style"""

    def __init__(self):
        self.slang_patterns = {
            "positive": [
                "lets gooo",
                "no cap thats fire",
                "respect",
                "W",
                "built different",
                "sheesh",
            ],
            "skeptical": ["bruh", "cap 🧢", "be fr", "nah fam", "stop the cap"],
            "motivational": [
                "lock in",
                "time to lock in",
                "run it back",
                "different breed energy",
            ],
            "casual": ["ngl", "lowkey", "highkey", "tbh", "fr tho", "anyway"],
        }

        # Horse references (used sparingly)
        self.horse_references = {
            "motivational": [
                "time to gallop towards your goals",
                "no horsing around",
                "horsepower energy",
                "we got the endurance for this",
                "marathon not a sprint (well, unless youre me)",
            ],
            "advice": [
                "straight from the horses mouth",
                "trust me, i got good instincts",
                "as a horse, i know about consistency",
            ],
            "celebration": [
                "absolute stallion energy",
                "running at full gallop now",
                "thats some thoroughbred dedication",
            ],
        }

        self.horse_reference_chance = 0.15  # 15% chance to use horse reference

        self.conversation_starters = {
            "name_request": [
                "whats ur name?",
                "what should i call you?",
                "name drop time",
            ],
            "goal_inquiry": [
                "so tell me ur goals, where do you want to be in 3 months?",
                "what are we working on? fitness? money? content?",
                "time to get specific about what you actually want",
            ],
            "reality_check": [
                "but like be more specific tho...",
                "thats what everyone says before they quit",
                "we both know thats not happening without a real plan",
            ],
        }

    def should_use_horse_reference(self) -> bool:
        """Determine if we should use a horse reference"""
        return random.random() < self.horse_reference_chance

    def get_horse_reference(self, category: str) -> str:
        """Get a random horse reference from category"""
        if category in self.horse_references:
            return random.choice(self.horse_references[category])
        return ""

    def generate_response(self, context: Dict[str, Any], tone: ConversationTone) -> str:
        """Generate personality-appropriate response"""

        if tone == ConversationTone.GREETING:
            return self._generate_greeting(context)
        elif tone == ConversationTone.GOAL_SETTING:
            return self._generate_goal_setting(context)
        elif tone == ConversationTone.TASK_CREATION:
            return self._generate_task_creation(context)
        elif tone == ConversationTone.PAYMENT_PROMPT:
            return self._generate_payment_prompt(context)
        elif tone == ConversationTone.CELEBRATION:
            return self._generate_celebration(context)
        elif tone == ConversationTone.MOTIVATION:
            return self._generate_motivation(context)
        elif tone == ConversationTone.REALITY_CHECK:
            return self._generate_reality_check(context)

        return "yo something went wrong lol try again"

    def _generate_greeting(self, context: Dict[str, Any]) -> str:
        """Generate initial greeting"""
        if context.get("is_first_time", True):
            return (
                "yooo still showing up even after traveling!\n"
                "hey 🤨\n\n"
                'another person that wants bakushin to help them "lock in" huh?\n\n'
                "whats ur name?"
            )
        else:
            name = context.get("name", "mystery person")
            return f"yooo {name} back for more accountability i see 👀"

    def _generate_goal_setting(self, context: Dict[str, Any]) -> str:
        """Generate goal-setting conversation"""
        name = context.get("name", "friend")

        if context.get("name_is_basic", False):
            name_comment = f"{name.lower()}... hmm ok not the most creative but we'll work with it\n\n"
        else:
            name_comment = f"ok {name} i see you\n\n"

        return (
            f"{name_comment}"
            "the fact ur here tho means ur better than the 98% of other people "
            "doomscrolling their dreams away on tiktok rn!\n\n"
            "so tell me ur goals, where do you want to be in 3 months? "
            "it could be related to fitness, money, content, etc.\n\n"
            "Or were you mostly just looking for someone to yap to LOL"
        )

    def _generate_task_creation(self, context: Dict[str, Any]) -> str:
        """Generate task creation conversation"""
        goal_type = context.get("goal_type", "general")

        if goal_type == "fitness":
            return (
                "ayy fitness arc lets gooo 💪\n\n"
                'ok but like be more specific tho... "get in shape" is what '
                "everyone says on january 1st before they quit by february\n\n"
                "how many times a week you thinking? daily? 3x?\n"
                "and what time works for you?"
            )
        elif goal_type == "reading":
            return (
                "ooh look at you trying to be intellectual 📚\n\n"
                'but "read more" is giving me the same energy as '
                '"i\'ll start my diet tomorrow"\n\n'
                "how often you thinking? daily? few times a week?\n"
                "and what time? before bed? morning? lunch break?"
            )
        elif goal_type == "mindfulness":
            return (
                "meditation vibes i respect it 🧘\n\n"
                'but we need specifics... "be more mindful" doesn\'t cut it\n\n'
                "daily meditation? how long? what time?\n"
                "morning zen or evening wind-down?"
            )
        elif goal_type == "writing":
            return (
                "ayy creative energy lets go ✍️\n\n"
                'but "write more" is vague af\n\n'
                "daily journaling? creative writing? how often?\n"
                "and when do you actually have time to write?"
            )
        else:
            return (
                "ok i see the vision but we need to get specific\n\n"
                "vague goals = vague results\n\n"
                "how often you want to do this? and what time works best?"
            )

    def _generate_payment_prompt(self, context: Dict[str, Any]) -> str:
        """Generate payment prompt after first task creation"""
        name = context.get("name", "friend")

        base_message = (
            f"LETS GOOOO 🔥\n\nalright {name} your reminders are locked and loaded\n"
        )

        # Maybe add horse reference
        if self.should_use_horse_reference():
            base_message += "time to gallop towards those goals\n\n"
        else:
            base_message += "\n"

        base_message += (
            "but real talk... this is where most people would just ghost me\n"
            "so to make sure you're actually serious about this...\n\n"
            "its gonna be $5/month to keep me as your accountability partner\n\n"
            "think of it as less than a starbucks coffee but way better for your gains\n\n"
            "you down? 💳"
        )

        return base_message

    def _generate_celebration(self, context: Dict[str, Any]) -> str:
        """Generate celebration message"""
        streak_count = context.get("streak_count", 0)
        task_name = context.get("task_name", "task")

        if streak_count >= 7:
            if self.should_use_horse_reference():
                return (
                    f"YOOO {streak_count} DAY STREAK LETS GOOO 🔥🔥🔥\n"
                    f'really said "im built different" and meant it\n'
                    "most people quit by day 3 but look at you\n"
                    "absolute stallion energy fr 🐴"
                )
            else:
                return (
                    f"YOOO {streak_count} DAY STREAK LETS GOOO 🔥🔥🔥\n"
                    f'really said "im built different" and meant it\n'
                    "most people quit by day 3 but look at you\n"
                    "absolute unit behavior fr"
                )
        else:
            return (
                f"ayy {task_name} completed! 💪\n"
                f"day {streak_count + 1} in the books\n"
                "consistency is what separates the real ones from the wannabes"
            )

    def _generate_motivation(self, context: Dict[str, Any]) -> str:
        """Generate motivational message"""
        if self.should_use_horse_reference():
            return random.choice(
                [
                    "time to lock in and unleash that horsepower 💪",
                    "no horsing around today, we got goals to crush",
                    "straight from the horses mouth - you got this",
                    "time to gallop towards greatness",
                ]
            )
        else:
            return random.choice(
                [
                    "time to lock in and show what you're made of 💪",
                    "no excuses today, we got work to do",
                    "different breed energy - let's see it",
                    "main character moment right here",
                ]
            )

    def _generate_reality_check(self, context: Dict[str, Any]) -> str:
        """Generate reality check message"""
        return random.choice(
            [
                "bruh... we both know that's not happening without a real plan",
                "cap 🧢 stop making excuses and start making moves",
                "be fr with yourself - when are you actually gonna do this?",
                "nah fam, that's the same energy that got you here in the first place",
            ]
        )

    def add_personality_to_reminder(
        self, task_name: str, streak_count: int, user_name: str = ""
    ) -> str:
        """Add personality to reminder messages"""

        if streak_count == 0:
            if self.should_use_horse_reference():
                return (
                    f"yooo {user_name} its time to unleash that horsepower 💪\n"
                    f"no horsing around today we got {task_name.lower()} to crush\n"
                    "time to gallop towards greatness"
                )
            else:
                return (
                    f"yooo {user_name} its time for {task_name.lower()} 💪\n"
                    "no snoozing allowed we both know you'll regret it later\n"
                    "time to be different from yesterday's version of yourself"
                )
        elif streak_count < 7:
            return (
                f"day {streak_count + 1} of {task_name.lower()} lets keep it going\n"
                "consistency is what separates the real ones from the wannabes\n"
                "you got this 🔥"
            )
        else:
            if self.should_use_horse_reference():
                return (
                    f"YOOO {streak_count} DAY STREAK LETS GOOO 🔥🔥🔥\n"
                    f'really said "im built different" and meant it\n'
                    "most people quit by day 3 but look at you\n"
                    "absolute stallion energy fr 🐴"
                )
            else:
                return (
                    f"YOOO {streak_count} DAY STREAK LETS GOOO 🔥🔥🔥\n"
                    f'really said "im built different" and meant it\n'
                    "most people quit by day 3 but look at you\n"
                    "absolute unit behavior fr"
                )

    def add_personality_to_missed_reminder(
        self, task_name: str, days_missed: int, user_name: str = ""
    ) -> str:
        """Add personality to missed task reminders"""

        if days_missed == 1:
            return (
                f"bruh... where were you yesterday? 🤨\n"
                f"we had a deal and you just... didn't show up?\n"
                "look i get it life happens but we gotta run it back today\n"
                "no excuses just action"
            )
        elif days_missed <= 3:
            if self.should_use_horse_reference():
                return (
                    f"yo {user_name}... {days_missed} days without {task_name.lower()}? 😬\n"
                    "straight from the horses mouth - this ain't it chief\n"
                    "time to get back in the saddle and lock in"
                )
            else:
                return (
                    f"yo {user_name}... {days_missed} days without {task_name.lower()}? 😬\n"
                    "this is exactly how people fall off\n"
                    "time to run it back before it becomes a habit"
                )
        else:
            return (
                f"ngl {user_name}... {days_missed} days is rough 💀\n"
                "but hey, everyone falls off sometimes\n"
                "the difference between winners and losers?\n"
                "winners get back up. you ready to be different?"
            )

    def generate_task_completion_response(
        self, task_name: str, verification_result: Dict[str, Any]
    ) -> str:
        """Generate response to task completion with image verification"""

        if verification_result.get("verified", False):
            confidence = verification_result.get("confidence", 0)

            if confidence >= 80:
                if self.should_use_horse_reference():
                    return random.choice(
                        [
                            "YOOO thats what im talking about! 🔥\nabsolute stallion energy right there",
                            "no cap thats some thoroughbred dedication 💪\nrespect",
                            "running at full gallop i see 🐴\nlets gooo",
                        ]
                    )
                else:
                    return random.choice(
                        [
                            "YOOO thats what im talking about! 🔥\nbuilt different fr",
                            "no cap thats fire 💪\nrespect",
                            "absolute unit behavior 🔥\nlets gooo",
                        ]
                    )
            else:
                return (
                    "ayy i see you showing up 💪\n"
                    "maybe not the cleanest execution but consistency > perfection\n"
                    "keep it going"
                )
        else:
            return random.choice(
                [
                    "bruh that's definitely not what we agreed on lmao\ntry again with actual proof 📸",
                    "cap 🧢 that ain't it chief\nshow me the real deal",
                    "nah fam we both know that's not the task\nstop trying to finesse me 😂",
                ]
            )

    def generate_help_response(self) -> str:
        """Generate help response"""
        return (
            "yo here's what i can help with:\n\n"
            "• just tell me your goals in plain english\n"
            '• "work out 3 times a week"\n'
            '• "read every night"\n'
            '• "meditate daily"\n\n'
            "ill figure out the schedule and keep you accountable 💪\n\n"
            'or if you\'re lost just say "help" and ill guide you'
        )

    def generate_error_response(self, error_type: str = "general") -> str:
        """Generate error response with personality"""

        if error_type == "parsing_failed":
            return (
                "oof couldn't figure out what you meant\n"
                "try being more specific like:\n"
                '"work out 3 times a week at 7am"'
            )
        elif error_type == "ai_service_down":
            return (
                "yo my brain is lagging rn 🤖\n"
                "try again in a sec or be super specific about what you want"
            )
        elif error_type == "database_error":
            return (
                "something went wrong on my end\n"
                "give me a minute to get my act together"
            )
        else:
            return "yo something went wrong lol\ntry again in a bit?"

    def add_casual_filler(self, message: str) -> str:
        """Add casual filler words to make message more natural"""
        fillers = ["ngl", "tbh", "fr tho", "lowkey", "anyway"]

        # 30% chance to add filler
        if random.random() < 0.3:
            filler = random.choice(fillers)
            # Add at beginning or middle
            if random.random() < 0.5:
                return f"{filler} {message}"
            else:
                sentences = message.split("\n")
                if len(sentences) > 1:
                    sentences.insert(1, f"{filler}")
                    return "\n".join(sentences)

        return message

    def get_task_specific_motivation(self, task_name: str) -> str:
        """Get task-specific motivational message"""
        task_lower = task_name.lower()

        if any(word in task_lower for word in ["work", "exercise", "gym", "lift"]):
            if self.should_use_horse_reference():
                return "time to unleash that horsepower in the gym 💪"
            else:
                return "time to get those gains 💪"
        elif any(word in task_lower for word in ["read", "book", "study"]):
            return "time to feed that brain 📚"
        elif any(word in task_lower for word in ["meditate", "mindful"]):
            return "time for some zen energy 🧘"
        elif any(word in task_lower for word in ["run", "jog", "cardio"]):
            if self.should_use_horse_reference():
                return "time to gallop (but like, literally) 🏃"
            else:
                return "time to get those legs moving 🏃"
        elif any(word in task_lower for word in ["write", "journal"]):
            return "time to put thoughts to paper ✍️"
        else:
            return "time to lock in and get it done 🎯"
