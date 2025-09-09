# Discord Task Reminder Bot - Architecture Plan

## Project Overview

A GPT-powered Discord bot that provides personalized daily task reminders with streak tracking and image verification for task completion.

## Core Features

- **Personal Task Management**: Users can set custom tasks with specific reminder times
- **Daily Reminders**: Automated notifications at user-specified times
- **Image Verification**: GPT Vision analysis to verify task completion through uploaded images
- **Streak Tracking**: Maintain and display user progress streaks
- **AI Personality**: Conversational responses using GPT-4o-mini with a 19-25 year old online male personality

## Technical Stack

### Backend

- **Language**: Python 3.11+
- **Discord Library**: discord.py 2.3+
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy with Alembic for migrations
- **Scheduling**: APScheduler for task reminders
- **AI Integration**: OpenAI API (GPT-4o-mini + Vision)
- **Environment**: Docker containers for deployment

### Key Dependencies

```
discord.py>=2.3.0
openai>=1.0.0
sqlalchemy>=2.0.0
alembic>=1.12.0
apscheduler>=3.10.0
psycopg2-binary>=2.9.0
python-dotenv>=1.0.0
pillow>=10.0.0
aiohttp>=3.8.0
```

## System Architecture

```mermaid
graph TB
    A[Discord User] -->|Commands| B[Discord Bot]
    B -->|Store Data| C[PostgreSQL Database]
    B -->|Schedule Tasks| D[APScheduler]
    B -->|Image Analysis| E[OpenAI Vision API]
    B -->|Conversations| F[OpenAI GPT-4o-mini]
    D -->|Trigger Reminders| B
    C -->|User Data| G[Users Table]
    C -->|Task Data| H[Tasks Table]
    C -->|Streak Data| I[Streaks Table]
    C -->|Completion Data| J[Completions Table]
```

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY,  -- Discord user ID
    username VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tasks Table

```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    reminder_time TIME NOT NULL,  -- Daily reminder time
    timezone VARCHAR(50) DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Streaks Table

```sql
CREATE TABLE streaks (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    task_id INTEGER REFERENCES tasks(id),
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_completion_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, task_id)
);
```

### Completions Table

```sql
CREATE TABLE completions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    task_id INTEGER REFERENCES tasks(id),
    completion_date DATE NOT NULL,
    image_url VARCHAR(500),
    verification_result TEXT,  -- GPT Vision analysis result
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Bot Commands Structure

### User Management

- `/register` - Register user with timezone
- `/profile` - View user profile and statistics
- `/timezone <timezone>` - Update user timezone

### Task Management

- `/create_task <name> <time> [description]` - Create new daily task
- `/list_tasks` - Show all user tasks
- `/edit_task <task_id> [name] [time] [description]` - Modify existing task
- `/delete_task <task_id>` - Remove a task
- `/toggle_task <task_id>` - Enable/disable task reminders

### Completion & Streaks

- `/complete <task_id> <image>` - Submit task completion with image
- `/streaks` - View current streaks for all tasks
- `/stats [task_id]` - Detailed statistics for tasks

### Utility

- `/help` - Show available commands
- `/ping` - Bot health check

## Core Components

### 1. Bot Manager (`bot.py`)

- Main Discord bot instance
- Command handling and routing
- Event listeners for messages and reactions

### 2. Database Manager (`database.py`)

- SQLAlchemy models and session management
- CRUD operations for all entities
- Database connection pooling

### 3. Task Scheduler (`scheduler.py`)

- APScheduler integration
- Daily reminder job management
- Timezone-aware scheduling

### 4. AI Integration (`ai_handler.py`)

- OpenAI API client
- GPT Vision image verification
- Conversational response generation
- Personality prompt management

### 5. Image Processor (`image_handler.py`)

- Image upload handling
- Format validation and resizing
- Temporary storage management

### 6. Streak Calculator (`streak_manager.py`)

- Streak calculation logic
- Statistics generation
- Progress tracking

## AI Personality System

### Conversation Prompt Template

```
You are a Discord bot helping users with daily task reminders and streak tracking.
Your personality is that of a 19-25 year old male who's very online and familiar with internet culture.

Key traits:
- Casual, friendly tone
- Uses modern slang appropriately
- Encouraging but not overly enthusiastic
- Slightly sarcastic humor when appropriate
- References to gaming, memes, and online culture
- Supportive of user goals

Context: {context}
User message: {message}
Task completion status: {completion_status}
Current streak: {streak}

Respond in character while being helpful about their task progress.
```

### Image Verification Prompt

```
Analyze this image to determine if the user has completed their task: "{task_name}"
Task description: "{task_description}"

Look for evidence that the task has been genuinely completed. Consider:
- Visual evidence of the activity
- Appropriate setting/context
- Realistic completion indicators

Respond with:
1. VERIFIED or NOT_VERIFIED
2. Brief explanation of your decision
3. Encouraging comment in the personality of a supportive online friend

Be reasonable but not overly strict in verification.
```

## Deployment Configuration

### Docker Setup

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

### Environment Variables

```env
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://user:pass@localhost:5432/taskbot
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Docker Compose

```yaml
version: "3.8"
services:
  bot:
    build: .
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/taskbot
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: taskbot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

## Security Considerations

- Environment variable management for API keys
- Input validation for all user commands
- Rate limiting for AI API calls
- Image size and format restrictions
- SQL injection prevention through ORM

## Cost Optimization

- GPT-4o-mini for cost-effective AI responses
- Image compression before Vision API calls
- Caching for frequently accessed data
- Efficient database queries with proper indexing
- Connection pooling for database and API calls

## Error Handling Strategy

- Graceful degradation when AI services are unavailable
- Retry logic for transient failures
- User-friendly error messages
- Comprehensive logging for debugging
- Fallback mechanisms for critical features

## Testing Strategy

- Unit tests for core business logic
- Integration tests for database operations
- Mock testing for external API calls
- Discord bot testing with test server
- Load testing for scheduler performance
