# Discord Task Reminder Bot 🤖

A GPT-powered Discord bot that helps you stay on track with daily tasks through personalized reminders, streak tracking, and AI-powered image verification.

## ✨ Features

- **📋 Personal Task Management**: Create custom daily tasks with specific reminder times
- **⏰ Smart Reminders**: Timezone-aware daily notifications
- **🔍 AI Image Verification**: GPT Vision analyzes uploaded images to verify task completion
- **🔥 Streak Tracking**: Maintain and track your progress streaks with motivation
- **🤖 Personality**: Conversational AI with the personality of a supportive online friend
- **💰 Cost Optimized**: Uses GPT-4o-mini for maximum affordability
- **🐳 Docker Ready**: Easy deployment with Docker containers

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Discord Bot Token
- OpenAI API Key
- PostgreSQL database (or use included Docker setup)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd discord-task-bot
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your credentials:

```env
DISCORD_TOKEN=your_discord_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
POSTGRES_PASSWORD=your_secure_password
```

### 3. Run with Docker

```bash
# Production
docker-compose up -d

# Development
docker-compose -f docker-compose.dev.yml up
```

### 4. Invite Bot to Server

Use this URL (replace YOUR_CLIENT_ID):

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2147549312&scope=bot%20applications.commands
```

## 📖 Usage

### Getting Started

1. **Register**: `/register [timezone]` - Set up your account
2. **Create Task**: `/create_task "Exercise" "07:00" "Morning workout"` - Add a daily task
3. **Complete Task**: `/complete 1 [image]` - Submit completion with image proof
4. **View Progress**: `/streaks` - Check your current streaks

### Available Commands

#### 👤 User Management

- `/register [timezone]` - Register your account with optional timezone
- `/profile` - View your profile and statistics
- `/timezone <timezone>` - Update your timezone

#### 📋 Task Management

- `/create_task <name> <time> [description]` - Create a new daily task
- `/list_tasks` - View all your tasks
- `/edit_task <id> [name] [time] [description]` - Modify existing task
- `/delete_task <id>` - Remove a task permanently
- `/toggle_task <id>` - Enable/disable task reminders

#### ✅ Completion & Tracking

- `/complete <task_id> <image>` - Complete task with image verification
- `/streaks` - View your current streaks
- `/stats [task_id]` - View detailed statistics
- `/help` - Show all available commands

## 🏗️ Architecture

### Tech Stack

- **Backend**: Python 3.11+ with discord.py
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI**: OpenAI GPT-4o-mini + Vision API
- **Scheduling**: APScheduler for daily reminders
- **Deployment**: Docker containers

### Project Structure

```
discord-task-bot/
├── src/
│   ├── main.py              # Bot entry point
│   ├── bot.py               # Discord bot setup
│   ├── config.py            # Configuration management
│   ├── database/
│   │   ├── models.py        # SQLAlchemy models
│   │   └── connection.py    # Database connection
│   ├── services/
│   │   ├── ai_handler.py    # OpenAI integration
│   │   ├── scheduler.py     # Task scheduling
│   │   └── streak_manager.py # Streak calculations
│   └── commands/
│       ├── user_commands.py     # User management
│       ├── task_commands.py     # Task CRUD
│       └── completion_commands.py # Task completion
├── docker-compose.yml       # Production deployment
├── docker-compose.dev.yml   # Development setup
├── Dockerfile              # Container definition
└── requirements.txt        # Python dependencies
```

## 💰 Cost Analysis

The bot is designed to be extremely cost-effective:

| Users | Monthly Cost | Breakdown            |
| ----- | ------------ | -------------------- |
| 100   | ~$0.79       | OpenAI API only      |
| 500   | ~$16.95      | API + Infrastructure |
| 1000  | ~$29.40      | Full scale           |

### Cost Optimization Features

- Smart response caching (30-40% savings)
- Daily API usage limits per user
- Efficient prompt engineering
- Batch processing for reminders

## 🔧 Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run locally
python src/main.py
```

### Database Migrations

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Testing

```bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src
```

## 🚀 Deployment

### Production Deployment

1. **Prepare Environment**:

   ```bash
   cp .env.example .env
   # Configure production values
   ```

2. **Deploy with Docker**:

   ```bash
   docker-compose up -d
   ```

3. **Monitor Logs**:
   ```bash
   docker-compose logs -f bot
   ```

### Scaling Considerations

- Use external PostgreSQL for multiple instances
- Implement Redis for session storage
- Set up load balancer for high availability
- Monitor API usage and costs

## 🔒 Security

- Environment variables for sensitive data
- Input validation for all commands
- Rate limiting for API calls
- Image size and format restrictions
- Non-root Docker containers

## 📊 Monitoring

### Health Checks

- Database connectivity
- API service availability
- Scheduler status
- Memory and CPU usage

### Logging

- Structured logging with different levels
- Error tracking and alerting
- API usage monitoring
- Performance metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- Check the [Setup Guide](SETUP_GUIDE.md) for detailed instructions
- Review the [Architecture Documentation](ARCHITECTURE.md) for technical details
- Open an issue for bugs or feature requests

## 🎯 Roadmap

- [ ] Web dashboard for task management
- [ ] Mobile app integration
- [ ] Advanced analytics and insights
- [ ] Team/group task challenges
- [ ] Integration with fitness trackers
- [ ] Custom AI personality training

---

Built with ❤️ for productivity enthusiasts who want to build lasting habits! 🔥
