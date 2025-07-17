#!/bin/bash

# Production deployment script for enhanced image processing system
# Optimized for no-GPU environment with Google Cloud Vision API

set -e  # Exit on any error

echo "🚀 Starting production deployment for Rethinking Park API..."

# Configuration
DEPLOYMENT_DIR="deployment"
DOCKER_COMPOSE_FILE="$DEPLOYMENT_DIR/production.yml"
ENV_FILE=".env.production"
SERVICE_ACCOUNT_KEY="service-account-key.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
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
    
    # Check if deployment directory exists
    if [ ! -d "$DEPLOYMENT_DIR" ]; then
        error "Deployment directory not found: $DEPLOYMENT_DIR"
        exit 1
    fi
    
    # Check if Docker Compose file exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Validate environment configuration
validate_environment() {
    log "Validating environment configuration..."
    
    # Check for required environment variables
    required_vars=(
        "GOOGLE_CLOUD_PROJECT"
        "GCS_BUCKET_NAME"
    )
    
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            error "  - $var"
        done
        error "Please set these variables in your environment or $ENV_FILE file"
        exit 1
    fi
    
    # Check for service account key
    if [ ! -f "$SERVICE_ACCOUNT_KEY" ]; then
        error "Google Cloud service account key not found: $SERVICE_ACCOUNT_KEY"
        error "Please place your service account key file in the project root"
        exit 1
    fi
    
    success "Environment configuration validated"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    directories=(
        "logs"
        "cache"
        "deployment/ssl"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log "Created directory: $dir"
        fi
    done
    
    success "Directories created"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    # Build the main API image
    docker build -t rethinking-park-api:production \
        --build-arg ENVIRONMENT=production \
        --file Dockerfile .
    
    if [ $? -eq 0 ]; then
        success "Docker image built successfully"
    else
        error "Failed to build Docker image"
        exit 1
    fi
}

# Deploy services
deploy_services() {
    log "Deploying services with Docker Compose..."
    
    # Stop existing services if running
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
    
    # Start services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    if [ $? -eq 0 ]; then
        success "Services deployed successfully"
    else
        error "Failed to deploy services"
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
        sleep 10
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
    
    # Wait for Nginx
    if curl -f -s http://localhost/health > /dev/null 2>&1; then
        success "Nginx service is ready"
    else
        warning "Nginx service may not be ready"
    fi
}

# Run health checks
run_health_checks() {
    log "Running comprehensive health checks..."
    
    # API health check
    api_health=$(curl -s http://localhost:8000/api/v1/health-detailed)
    if echo "$api_health" | grep -q '"status": "healthy"'; then
        success "API health check passed"
    else
        warning "API health check shows issues"
        echo "$api_health" | jq '.' 2>/dev/null || echo "$api_health"
    fi
    
    # Performance metrics check
    metrics=$(curl -s http://localhost:8000/api/v1/metrics)
    if [ $? -eq 0 ]; then
        success "Performance metrics endpoint accessible"
    else
        warning "Performance metrics endpoint not accessible"
    fi
    
    # Vision API check
    vision_metrics=$(curl -s http://localhost:8000/api/v1/vision-api-metrics)
    if [ $? -eq 0 ]; then
        success "Vision API metrics endpoint accessible"
    else
        warning "Vision API metrics endpoint not accessible"
    fi
}

# Display deployment information
show_deployment_info() {
    log "Deployment completed successfully!"
    echo
    echo "📋 Deployment Information:"
    echo "=========================="
    echo "🌐 API Endpoint: http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/docs"
    echo "🔍 Health Check: http://localhost:8000/api/v1/health-detailed"
    echo "📊 Metrics: http://localhost:8000/api/v1/metrics"
    echo "🎯 Prometheus: http://localhost:9090"
    echo "🔧 Nginx: http://localhost"
    echo
    echo "🐳 Docker Services:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    echo
    echo "📈 Performance Features:"
    echo "  ✅ Google Vision API call batching"
    echo "  ✅ Memory optimization for no-GPU environment"
    echo "  ✅ Redis caching with LRU eviction"
    echo "  ✅ Async processing for batch operations"
    echo "  ✅ CDN-like image delivery with Nginx"
    echo "  ✅ Comprehensive monitoring and logging"
    echo
    echo "🔧 Management Commands:"
    echo "  View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "  Stop services: docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "  Restart services: docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo "  Scale API: docker-compose -f $DOCKER_COMPOSE_FILE up -d --scale rethinking-park-api=3"
    echo
}

# Cleanup function
cleanup() {
    if [ $? -ne 0 ]; then
        error "Deployment failed. Cleaning up..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Main deployment process
main() {
    log "Starting production deployment process..."
    
    check_prerequisites
    validate_environment
    create_directories
    build_images
    deploy_services
    wait_for_services
    run_health_checks
    show_deployment_info
    
    success "🎉 Production deployment completed successfully!"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log "Stopping services..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
        success "Services stopped"
        ;;
    "restart")
        log "Restarting services..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" restart
        success "Services restarted"
        ;;
    "logs")
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
        ;;
    "status")
        docker-compose -f "$DOCKER_COMPOSE_FILE" ps
        ;;
    "health")
        curl -s http://localhost:8000/api/v1/health-detailed | jq '.'
        ;;
    "metrics")
        curl -s http://localhost:8000/api/v1/metrics | jq '.'
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|health|metrics}"
        echo
        echo "Commands:"
        echo "  deploy  - Deploy the production environment (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - Show service logs"
        echo "  status  - Show service status"
        echo "  health  - Show health check results"
        echo "  metrics - Show system metrics"
        exit 1
        ;;
esac