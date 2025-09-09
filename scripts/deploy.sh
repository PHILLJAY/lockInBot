#!/bin/bash

# Discord Task Reminder Bot - Deployment Script

set -e  # Exit on any error

echo "🚀 Starting Discord Task Reminder Bot deployment..."

# Check if required environment variables are set
check_env_vars() {
    echo "📋 Checking environment variables..."
    
    required_vars=("DISCORD_TOKEN" "OPENAI_API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo "❌ Missing required environment variables:"
        printf '   %s\n' "${missing_vars[@]}"
        echo "Please set these variables in your .env file or environment."
        exit 1
    fi
    
    echo "✅ All required environment variables are set"
}

# Check if Docker is installed and running
check_docker() {
    echo "🐳 Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "❌ Docker is not running. Please start Docker first."
        exit 1
    fi
    
    echo "✅ Docker is installed and running"
}

# Check if Docker Compose is available
check_docker_compose() {
    echo "📦 Checking Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        echo "❌ Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    echo "✅ Docker Compose is available: $COMPOSE_CMD"
}

# Create necessary directories
create_directories() {
    echo "📁 Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p backups
    
    echo "✅ Directories created"
}

# Build and start services
deploy_services() {
    echo "🔨 Building and starting services..."
    
    # Stop any existing services
    echo "Stopping existing services..."
    $COMPOSE_CMD down --remove-orphans || true
    
    # Build and start services
    echo "Building and starting new services..."
    $COMPOSE_CMD up -d --build
    
    echo "✅ Services started successfully"
}

# Wait for database to be ready
wait_for_database() {
    echo "⏳ Waiting for database to be ready..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if $COMPOSE_CMD exec -T db pg_isready -U postgres -d taskbot &> /dev/null; then
            echo "✅ Database is ready"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: Database not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ Database failed to start within expected time"
    exit 1
}

# Run database migrations
run_migrations() {
    echo "🗃️ Running database migrations..."
    
    # Note: In a real deployment, you'd run Alembic migrations here
    # For now, the bot creates tables automatically on startup
    echo "✅ Database migrations completed (auto-creation enabled)"
}

# Check service health
check_health() {
    echo "🏥 Checking service health..."
    
    # Check if bot container is running
    if ! $COMPOSE_CMD ps bot | grep -q "Up"; then
        echo "❌ Bot service is not running"
        echo "Checking logs..."
        $COMPOSE_CMD logs bot
        exit 1
    fi
    
    # Check if database container is running
    if ! $COMPOSE_CMD ps db | grep -q "Up"; then
        echo "❌ Database service is not running"
        echo "Checking logs..."
        $COMPOSE_CMD logs db
        exit 1
    fi
    
    echo "✅ All services are healthy"
}

# Show deployment status
show_status() {
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📊 Service Status:"
    $COMPOSE_CMD ps
    echo ""
    echo "📝 Useful Commands:"
    echo "  View logs:           $COMPOSE_CMD logs -f"
    echo "  View bot logs:       $COMPOSE_CMD logs -f bot"
    echo "  View database logs:  $COMPOSE_CMD logs -f db"
    echo "  Stop services:       $COMPOSE_CMD down"
    echo "  Restart bot:         $COMPOSE_CMD restart bot"
    echo "  Update bot:          $COMPOSE_CMD up -d --build bot"
    echo ""
    echo "🔗 Next Steps:"
    echo "  1. Invite the bot to your Discord server"
    echo "  2. Use /register to set up your account"
    echo "  3. Create your first task with /create_task"
    echo ""
}

# Main deployment function
main() {
    echo "Discord Task Reminder Bot - Deployment Script"
    echo "=============================================="
    echo ""
    
    # Load environment variables if .env exists
    if [ -f .env ]; then
        echo "📄 Loading environment variables from .env file..."
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    # Run deployment steps
    check_env_vars
    check_docker
    check_docker_compose
    create_directories
    deploy_services
    wait_for_database
    run_migrations
    
    # Give services a moment to fully start
    echo "⏳ Waiting for services to fully initialize..."
    sleep 10
    
    check_health
    show_status
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        echo "🛑 Stopping services..."
        $COMPOSE_CMD down
        echo "✅ Services stopped"
        ;;
    "restart")
        echo "🔄 Restarting services..."
        $COMPOSE_CMD restart
        echo "✅ Services restarted"
        ;;
    "logs")
        echo "📝 Showing logs..."
        $COMPOSE_CMD logs -f
        ;;
    "status")
        echo "📊 Service status:"
        $COMPOSE_CMD ps
        ;;
    "update")
        echo "🔄 Updating bot..."
        $COMPOSE_CMD up -d --build bot
        echo "✅ Bot updated"
        ;;
    *)
        echo "Usage: $0 [deploy|stop|restart|logs|status|update]"
        echo ""
        echo "Commands:"
        echo "  deploy   - Deploy the bot (default)"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show service logs"
        echo "  status   - Show service status"
        echo "  update   - Update and restart bot only"
        exit 1
        ;;
esac