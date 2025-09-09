# Discord Task Bot - Setup Guide

## Prerequisites

### Required Accounts & API Keys

1. **Discord Developer Account**

   - Create application at https://discord.com/developers/applications
   - Generate bot token
   - Set up OAuth2 permissions

2. **OpenAI Account**

   - Sign up at https://platform.openai.com
   - Generate API key
   - Set up billing (pay-as-you-go recommended)

3. **Database Hosting** (Choose one)
   - Local PostgreSQL installation
   - Cloud provider (AWS RDS, Google Cloud SQL, etc.)
   - Free tier options (ElephantSQL, Supabase)

### Development Environment

- Python 3.11 or higher
- Docker and Docker Compose
- Git for version control
- Code editor (VS Code recommended)

## Discord Bot Setup

### 1. Create Discord Application

```bash
# Visit https://discord.com/developers/applications
# Click "New Application"
# Name: "Task Reminder Bot"
# Navigate to "Bot" section
# Click "Add Bot"
# Copy the bot token (keep this secret!)
```

### 2. Bot Permissions

Required permissions for the bot:

- `Send Messages` (2048)
- `Use Slash Commands` (2147483648)
- `Attach Files` (32768)
- `Embed Links` (16384)
- `Read Message History` (65536)
- `Add Reactions` (64)

**Permission Integer**: `2147549312`

### 3. Invite Bot to Server

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2147549312&scope=bot%20applications.commands
```

## OpenAI API Setup

### 1. API Key Generation

```bash
# Visit https://platform.openai.com/api-keys
# Click "Create new secret key"
# Name: "Discord Task Bot"
# Copy the API key (starts with sk-)
```

### 2. Cost Optimization Settings

```python
# Recommended settings for cost efficiency:
OPENAI_MODEL = "gpt-4o-mini"  # Most cost-effective
MAX_TOKENS = 150              # Limit response length
TEMPERATURE = 0.7             # Balance creativity/consistency
```

## Database Setup Options

### Option 1: Local PostgreSQL (Development)

```bash
# Install PostgreSQL
# Windows: Download from postgresql.org
# macOS: brew install postgresql
# Linux: sudo apt-get install postgresql

# Create database
createdb taskbot_dev

# Set connection string
DATABASE_URL=postgresql://username:password@localhost:5432/taskbot_dev
```

### Option 2: Docker PostgreSQL (Recommended)

```yaml
# Already included in docker-compose.yml
# No additional setup required
# Database will be created automatically
```

### Option 3: Cloud Database (Production)

```bash
# ElephantSQL (Free tier: 20MB)
# 1. Sign up at elephantsql.com
# 2. Create new instance
# 3. Copy connection URL

# Supabase (Free tier: 500MB)
# 1. Sign up at supabase.com
# 2. Create new project
# 3. Get connection string from settings

# AWS RDS (Pay-as-you-go)
# 1. Create RDS PostgreSQL instance
# 2. Configure security groups
# 3. Get endpoint URL
```

## Environment Configuration

### 1. Create Environment File

```bash
# Copy example file
cp .env.example .env

# Edit with your values
nano .env
```

### 2. Environment Variables

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_server_id_here  # Optional: for guild-specific commands

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=150

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/taskbot

# Bot Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
COMMAND_PREFIX=/
MAX_IMAGE_SIZE_MB=10
REMINDER_CHANNEL_NAME=task-reminders

# Timezone Configuration (Optional)
DEFAULT_TIMEZONE=UTC
```

## Installation & Running

### Method 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd discord-task-bot

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop the bot
docker-compose down
```

### Method 2: Local Development

```bash
# Clone the repository
git clone <repository-url>
cd discord-task-bot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up database
alembic upgrade head

# Run the bot
python src/main.py
```

## Database Migration

### Initial Setup

```bash
# Initialize Alembic (only needed once)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial tables"

# Apply migrations
alembic upgrade head
```

### Future Updates

```bash
# Create new migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Apply new migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## Testing the Bot

### 1. Basic Functionality Test

```bash
# In Discord, try these commands:
/help                           # Should show available commands
/register                       # Register your user account
/create_task "Exercise" "07:00" # Create a test task
/list_tasks                     # View your tasks
```

### 2. Image Verification Test

```bash
# Upload an image with the completion command
/complete 1 [attach image]      # Complete task with image
# Bot should analyze image and respond
```

### 3. Reminder Test

```bash
# Set a task for a few minutes from now
/create_task "Test Reminder" "14:35"  # Use current time + 2 minutes
# Wait for reminder to be sent
```

## Troubleshooting

### Common Issues

#### Bot Not Responding

```bash
# Check bot status
docker-compose logs bot

# Verify token is correct
# Check bot permissions in Discord server
# Ensure bot is online in Discord
```

#### Database Connection Errors

```bash
# Check database is running
docker-compose ps

# Verify connection string
echo $DATABASE_URL

# Check database logs
docker-compose logs db
```

#### OpenAI API Errors

```bash
# Verify API key is valid
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check API usage and billing
# Visit https://platform.openai.com/usage
```

#### Timezone Issues

```bash
# List available timezones
python -c "import pytz; print(pytz.all_timezones)"

# Test timezone conversion
python -c "
from datetime import datetime
import pytz
tz = pytz.timezone('America/Toronto')
print(datetime.now(tz))
"
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python src/main.py --debug

# Check specific component logs
docker-compose logs -f bot | grep "scheduler"
```

## Performance Monitoring

### Resource Usage

```bash
# Monitor Docker containers
docker stats

# Check database performance
docker-compose exec db psql -U postgres -d taskbot -c "
SELECT schemaname,tablename,attname,n_distinct,correlation
FROM pg_stats WHERE tablename IN ('users','tasks','streaks','completions');
"
```

### API Usage Tracking

```python
# Monitor OpenAI API usage
# Check dashboard at https://platform.openai.com/usage

# Set up usage alerts
# Configure billing limits in OpenAI dashboard
```

## Security Checklist

### Environment Security

- [ ] Bot token stored in environment variables (not code)
- [ ] OpenAI API key secured
- [ ] Database credentials protected
- [ ] `.env` file added to `.gitignore`
- [ ] Production environment variables secured

### Bot Security

- [ ] Minimal Discord permissions granted
- [ ] Input validation implemented
- [ ] Rate limiting configured
- [ ] Image size limits enforced
- [ ] SQL injection prevention (using ORM)

### Database Security

- [ ] Database user has minimal required permissions
- [ ] Connection encryption enabled (SSL)
- [ ] Regular backups configured
- [ ] Access logs monitored

## Backup & Recovery

### Database Backup

```bash
# Create backup
docker-compose exec db pg_dump -U postgres taskbot > backup.sql

# Restore backup
docker-compose exec -T db psql -U postgres taskbot < backup.sql
```

### Configuration Backup

```bash
# Backup environment configuration
cp .env .env.backup

# Backup Docker configuration
cp docker-compose.yml docker-compose.yml.backup
```

## Scaling Considerations

### Horizontal Scaling

- Use external database (not Docker container)
- Implement Redis for session storage
- Load balancer for multiple bot instances
- Shared file storage for images

### Performance Optimization

- Database connection pooling
- API response caching
- Batch processing for reminders
- Async operations for all I/O

This setup guide provides everything needed to get your Discord task reminder bot running in both development and production environments.
