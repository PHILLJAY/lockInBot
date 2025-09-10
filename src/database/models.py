"""
Database models for the Discord Task Reminder Bot.
"""

from datetime import datetime, date
from typing import Optional, List, Dict
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    Time,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped

Base = declarative_base()


class User(Base):
    """User model for storing Discord user information."""

    __tablename__ = "users"

    id: Mapped[int] = Column(BigInteger, primary_key=True)  # Discord user ID
    username: Mapped[str] = Column(String(255), nullable=False)
    timezone: Mapped[str] = Column(String(50), default="UTC", nullable=False)
    created_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_active: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # API usage tracking
    daily_api_calls: Mapped[int] = Column(Integer, default=0, nullable=False)
    last_api_reset: Mapped[date] = Column(Date, default=date.today, nullable=False)

    # Relationships
    tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="user", cascade="all, delete-orphan"
    )
    streaks: Mapped[List["Streak"]] = relationship(
        "Streak", back_populates="user", cascade="all, delete-orphan"
    )
    completions: Mapped[List["Completion"]] = relationship(
        "Completion", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', timezone='{self.timezone}')>"


class Task(Base):
    """Task model for storing user-defined tasks."""

    __tablename__ = "tasks"

    id: Mapped[int] = Column(Integer, primary_key=True)
    user_id: Mapped[int] = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = Column(String(255), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    reminder_time: Mapped[str] = Column(Time, nullable=False)  # Daily reminder time
    timezone: Mapped[str] = Column(String(50), default="UTC", nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    streaks: Mapped[List["Streak"]] = relationship(
        "Streak", back_populates="task", cascade="all, delete-orphan"
    )
    completions: Mapped[List["Completion"]] = relationship(
        "Completion", back_populates="task", cascade="all, delete-orphan"
    )

    # Enhanced fields for natural language task creation
    generation_method: Mapped[Optional[str]] = Column(String(50), default="manual")
    parent_request_id: Mapped[Optional[str]] = Column(
        String(36)
    )  # UUID for grouping related tasks
    scheduling_pattern: Mapped[Optional[str]] = Column(
        Text
    )  # JSON string of original pattern

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name='{self.name}', user_id={self.user_id}, active={self.is_active})>"


class Streak(Base):
    """Streak model for tracking user task completion streaks."""

    __tablename__ = "streaks"

    id: Mapped[int] = Column(Integer, primary_key=True)
    user_id: Mapped[int] = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int] = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    current_streak: Mapped[int] = Column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = Column(Integer, default=0, nullable=False)
    last_completion_date: Mapped[Optional[date]] = Column(Date)
    created_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="streaks")
    task: Mapped["Task"] = relationship("Task", back_populates="streaks")

    def __repr__(self) -> str:
        return f"<Streak(id={self.id}, user_id={self.user_id}, task_id={self.task_id}, current={self.current_streak}, longest={self.longest_streak})>"


class Completion(Base):
    """Completion model for storing task completion records with image verification."""

    __tablename__ = "completions"

    id: Mapped[int] = Column(Integer, primary_key=True)
    user_id: Mapped[int] = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int] = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    completion_date: Mapped[date] = Column(Date, nullable=False)
    image_url: Mapped[Optional[str]] = Column(String(500))
    verification_result: Mapped[Optional[str]] = Column(
        Text
    )  # GPT Vision analysis result
    verified: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    ai_confidence: Mapped[Optional[float]] = Column(Integer)  # Confidence score 0-100
    created_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="completions")
    task: Mapped["Task"] = relationship("Task", back_populates="completions")

    def __repr__(self) -> str:
        return f"<Completion(id={self.id}, user_id={self.user_id}, task_id={self.task_id}, verified={self.verified}, date={self.completion_date})>"


class APIUsage(Base):
    """API usage tracking for cost management."""

    __tablename__ = "api_usage"

    id: Mapped[int] = Column(Integer, primary_key=True)
    user_id: Mapped[int] = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    endpoint: Mapped[str] = Column(
        String(100), nullable=False
    )  # 'chat', 'vision', etc.
    tokens_used: Mapped[int] = Column(Integer, nullable=False)
    estimated_cost: Mapped[float] = Column(Integer, nullable=False)  # In USD cents
    created_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<APIUsage(id={self.id}, user_id={self.user_id}, endpoint='{self.endpoint}', tokens={self.tokens_used}, cost=${self.estimated_cost / 100:.4f})>"


class DMConversation(Base):
    """DM conversation state for multi-turn task creation."""

    __tablename__ = "dm_conversations"

    user_id: Mapped[int] = Column(BigInteger, primary_key=True)  # Discord user ID
    state: Mapped[str] = Column(String(50), nullable=False)
    context: Mapped[Dict] = Column(Text, nullable=False)  # JSON string
    last_interaction: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = Column(DateTime, nullable=False)
    pending_tasks: Mapped[Optional[str]] = Column(Text)  # JSON string

    def __repr__(self) -> str:
        return f"<DMConversation(user_id={self.user_id}, state='{self.state}', expires_at={self.expires_at})>"
