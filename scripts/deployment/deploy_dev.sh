#!/bin/bash

# Development environment deployment script
# Optimized for local development with debugging features

set -e

echo "🚀 Starting development deployment for Rethinking Park API..."

# Configuration
DOCKER_COMPOSE_FILE="deployment/docker-compose.dev.yml"
ENV_FILE=".env.development"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker Compose file exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Create development environment file if it doesn't exist
setup_environment() {
    log "Setting up development environment..."
    
    if [ ! -f "$ENV_FILE" ]; then
        log "Creating development environment file..."
        cat > "$ENV_FILE" << EOF
# Development Environment Configuration
GOOGLE_CLOUD_PROJECT=rethinking-park-dev
GCS_BUCKET_NAME=rethinking-park-images-dev
REDIS_URL=redis://redis:6379/0
DEBUG=true
LOG_LEVEL=DEBUG
RATE_LIMIT_ENABLED=false
EOF
        success "Development environment file created: $ENV_FILE"
    else
        log "Development environment file already exists"
    fi
}

# Build and start services
deploy_services() {
    log "Building and starting development services..."
    
    # Stop existing services if running
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
    
    # Build and start services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up --build -d
    
    if [ $? -eq 0 ]; then
        success "Development services started successfully"
    else
        error "Failed to start development services"
        exit 1
    fi
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    # Wait for API service
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            success "API service is ready"
            break
        fi
        
        attempt=$((attempt + 1))
        log "Waiting for API service... (attempt $attempt/$max_attempts)"
        sleep 5
    done
    
    if [ $attempt -eq $max_attempts ]; then
        error "API service failed to start within expected time"
        exit 1
    fi
    
    # Wait for Redis
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
        success "Redis service is ready"
    else
        warning "Redis service may not be ready"
    fi
}

# Show development information
show_development_info() {
    log "Development deployment completed successfully!"
    echo
    echo "📋 Development Environment Information:"
    echo "======================================"
    echo "🌐 API Endpoint: http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/docs"
    echo "🔍 Health Check: http://localhost:8000/health"
    echo "🐛 Debug Port: 5678 (if enabled)"
    echo "📊 Redis Commander: http://localhost:8081"
    echo
    echo "🐳 Docker Services:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    echo
    echo "🔧 Development Features:"
    echo "  ✅ Hot reload enabled"
    echo "  ✅ Debug mode enabled"
    echo "  ✅ Verbose logging"
    echo "  ✅ Redis Commander UI"
    echo "  ✅ No rate limiting"
    echo "  ✅ Permissive CORS"
    echo
    echo "🔧 Management Commands:"
    echo "  View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "  Stop services: docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "  Restart services: docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo "  Shell access: docker-compose -f $DOCKER_COMPOSE_FILE exec rethinking-park-api bash"
    echo
}

# Main deployment process
main() {
    log "Starting development deployment process..."
    
    check_prerequisites
    setup_environment
    deploy_services
    wait_for_services
    show_development_info
    
    success "🎉 Development deployment completed successfully!"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log "Stopping development services..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
        success "Development services stopped"
        ;;
    "restart")
        log "Restarting development services..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" restart
        success "Development services restarted"
        ;;
    "logs")
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
        ;;
    "status")
        docker-compose -f "$DOCKER_COMPOSE_FILE" ps
        ;;
    "shell")
        docker-compose -f "$DOCKER_COMPOSE_FILE" exec rethinking-park-api bash
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|shell}"
        echo
        echo "Commands:"
        echo "  deploy  - Deploy the development environment (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - Show service logs"
        echo "  status  - Show service status"
        echo "  shell   - Access API container shell"
        exit 1
        ;;
esac