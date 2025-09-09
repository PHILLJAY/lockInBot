"""
AI handler for OpenAI GPT-4o-mini integration and image verification.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import openai
from openai import AsyncOpenAI

from config import Config

logger = logging.getLogger(__name__)


class AIHandler:
    """Handles all AI interactions including chat and image verification."""

    def __init__(self, config: Config):
        """Initialize the AI handler with OpenAI configuration."""
        self.config = config
        self.client = AsyncOpenAI(api_key=config.openai_api_key)

        # Personality prompt for the bot
        self.personality_prompt = self._build_personality_prompt()

        # Cost tracking
        self.daily_usage = {}
        self.last_reset = date.today()

    def _build_personality_prompt(self) -> str:
        """Build the personality prompt for the AI."""
        return """You are a Discord bot helping users with daily task reminders and streak tracking. 
Your personality is that of a 19-25 year old male who's very online and familiar with internet culture.

Key traits:
- Casual, friendly tone with modern slang
- Encouraging but not overly enthusiastic  
- Slightly sarcastic humor when appropriate
- References to gaming, memes, and online culture
- Supportive of user goals without being preachy
- Use emojis sparingly but effectively
- Keep responses concise (under 150 tokens)

Examples of your style:
- "yo nice streak! keep it going 💪"
- "bruh that's definitely not a workout pic lmao, try again"
- "streak broken but we've all been there, time to run it back"
- "that's some solid progress ngl, respect"
- "oof missed a day? happens to the best of us, let's get back on track"

Always be helpful about their task progress while maintaining this personality."""

    async def generate_response(
        self, user_message: str, context: Dict[str, Any], user_id: int
    ) -> str:
        """Generate a conversational response based on user message and context."""

        # Check daily limits
        if not self._check_daily_limit(user_id):
            return "yo you've hit your daily AI limit, try again tomorrow 🤖"

        try:
            # Build context string
            context_str = self._build_context_string(context)

            # Create the prompt
            prompt = f"""
{self.personality_prompt}

Context: {context_str}
User message: {user_message}

Respond in character while being helpful about their task progress.
"""

            # Make API call
            response = await self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[{"role": "system", "content": prompt}],
                max_tokens=self.config.openai_max_tokens,
                temperature=0.7,
            )

            # Track usage
            self._track_usage(user_id, "chat", response.usage.total_tokens)

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
            return "oof something went wrong with the AI, try again in a sec 🤖"

    async def verify_task_completion(
        self,
        image_url: str,
        task_name: str,
        task_description: Optional[str],
        user_id: int,
    ) -> Dict[str, Any]:
        """Verify task completion using GPT Vision."""

        # Check daily limits
        if not self._check_daily_limit(user_id):
            return {
                "verified": False,
                "confidence": 0,
                "explanation": "Daily AI limit reached, try again tomorrow",
                "response": "yo you've hit your daily AI limit, try again tomorrow 🤖",
            }

        try:
            # Build verification prompt
            prompt = f"""Analyze this image to determine if the user has completed their task: "{task_name}"
{f'Task description: "{task_description}"' if task_description else ""}

Look for evidence that the task has been genuinely completed. Consider:
- Visual evidence of the activity
- Appropriate setting/context  
- Realistic completion indicators

Respond with:
1. VERIFIED or NOT_VERIFIED
2. Confidence score (0-100)
3. Brief explanation of your decision
4. Encouraging comment in the personality of a supportive online friend (casual, modern slang)

Be reasonable but not overly strict in verification. Format your response as:
VERIFICATION: [VERIFIED/NOT_VERIFIED]
CONFIDENCE: [0-100]
EXPLANATION: [brief explanation]
RESPONSE: [encouraging comment in character]"""

            # Make Vision API call
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Vision model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=200,
            )

            # Parse response
            result = self._parse_verification_response(
                response.choices[0].message.content
            )

            # Track usage
            self._track_usage(user_id, "vision", response.usage.total_tokens)

            return result

        except Exception as e:
            logger.error(f"Failed to verify task completion: {e}")
            return {
                "verified": False,
                "confidence": 0,
                "explanation": f"AI verification failed: {str(e)}",
                "response": "oof couldn't analyze that image, try uploading again 📸",
            }

    def _build_context_string(self, context: Dict[str, Any]) -> str:
        """Build context string from provided context data."""
        parts = []

        if "current_streak" in context:
            parts.append(f"Current streak: {context['current_streak']} days")

        if "longest_streak" in context:
            parts.append(f"Longest streak: {context['longest_streak']} days")

        if "task_name" in context:
            parts.append(f"Task: {context['task_name']}")

        if "completion_status" in context:
            parts.append(f"Status: {context['completion_status']}")

        if "last_completion" in context:
            parts.append(f"Last completed: {context['last_completion']}")

        return ", ".join(parts) if parts else "No additional context"

    def _parse_verification_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the verification response from GPT Vision."""
        lines = response_text.strip().split("\n")
        result = {
            "verified": False,
            "confidence": 0,
            "explanation": "Could not parse verification response",
            "response": "hmm couldn't figure that out, try again? 🤔",
        }

        for line in lines:
            line = line.strip()
            if line.startswith("VERIFICATION:"):
                result["verified"] = "VERIFIED" in line.upper()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = int(line.split(":")[1].strip())
                    result["confidence"] = max(0, min(100, confidence))
                except (ValueError, IndexError):
                    pass
            elif line.startswith("EXPLANATION:"):
                result["explanation"] = line.split(":", 1)[1].strip()
            elif line.startswith("RESPONSE:"):
                result["response"] = line.split(":", 1)[1].strip()

        return result

    def _check_daily_limit(self, user_id: int) -> bool:
        """Check if user has exceeded daily API limit."""
        # Reset daily usage if it's a new day
        if date.today() > self.last_reset:
            self.daily_usage = {}
            self.last_reset = date.today()

        current_usage = self.daily_usage.get(user_id, 0)
        return current_usage < self.config.daily_api_limit_per_user

    def _track_usage(self, user_id: int, endpoint: str, tokens: int) -> None:
        """Track API usage for cost management."""
        # Reset daily usage if it's a new day
        if date.today() > self.last_reset:
            self.daily_usage = {}
            self.last_reset = date.today()

        # Update usage
        self.daily_usage[user_id] = self.daily_usage.get(user_id, 0) + 1

        # Calculate estimated cost (in cents)
        if endpoint == "chat":
            # GPT-4o-mini: $0.15 input, $0.60 output per 1M tokens
            # Rough estimate: 70% input, 30% output
            input_tokens = int(tokens * 0.7)
            output_tokens = int(tokens * 0.3)
            cost_cents = (input_tokens * 0.015 + output_tokens * 0.06) / 1000
        elif endpoint == "vision":
            # Vision API pricing
            cost_cents = tokens * 0.015 / 1000
        else:
            cost_cents = tokens * 0.01 / 1000  # Default estimate

        logger.debug(
            f"API usage - User: {user_id}, Endpoint: {endpoint}, Tokens: {tokens}, Cost: ${cost_cents / 100:.4f}"
        )

    async def get_usage_stats(self, user_id: int) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        current_usage = self.daily_usage.get(user_id, 0)
        remaining = max(0, self.config.daily_api_limit_per_user - current_usage)

        return {
            "daily_usage": current_usage,
            "daily_limit": self.config.daily_api_limit_per_user,
            "remaining": remaining,
            "reset_date": self.last_reset.isoformat(),
        }
