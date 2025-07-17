#!/bin/bash

# Staging environment deployment script
# Production-like environment for testing before deployment

set -e

echo "🚀 Starting staging deployment for Rethinking Park API..."

# Configuration
DOCKER_COMPOSE_FILE="deployment/docker-compose.staging.yml"
ENV_FILE=".env.staging"

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

# Validate environment configuration
validate_environment() {
    log "Validating staging environment configuration..."
    
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
    if [ ! -f "service-account-key.json" ]; then
        error "Google Cloud service account key not found: service-account-key.json"
        error "Please place your service account key file in the project root"
        exit 1
    fi
    
    success "Environment configuration validated"
}

# Build and deploy services
deploy_services() {
    log "Building and deploying staging services..."
    
    # Stop existing services if running
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
    
    # Build and start services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up --build -d
    
    if [ $? -eq 0 ]; then
        success "Staging services deployed successfully"
    else
        error "Failed to deploy staging services"
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

# Run staging tests
run_staging_tests() {
    log "Running staging environment tests..."
    
    # API health check
    api_health=$(curl -s http://localhost:8000/api/v1/health-detailed)
    if echo "$api_health" | grep -q '"status": "healthy"'; then
        success "API health check passed"
    else
        warning "API health check shows issues"
        echo "$api_health" | jq '.' 2>/dev/null || echo "$api_health"
    fi
    
    # Performance test
    log "Running basic performance test..."
    if command -v ab &> /dev/null; then
        ab -n 100 -c 10 http://localhost:8000/health > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            success "Basic performance test passed"
        else
            warning "Performance test failed"
        fi
    else
        warning "Apache Bench (ab) not available, skipping performance test"
    fi
}

# Show staging information
show_staging_info() {
    log "Staging deployment completed successfully!"
    echo
    echo "📋 Staging Environment Information:"
    echo "=================================="
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
    echo "📈 Staging Features:"
    echo "  ✅ Production-like configuration"
    echo "  ✅ Performance optimization enabled"
    echo "  ✅ Rate limiting enabled"
    echo "  ✅ Monitoring and metrics"
    echo "  ✅ Nginx reverse proxy"
    echo "  ✅ Resource limits applied"
    echo
    echo "🔧 Management Commands:"
    echo "  View logs: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "  Stop services: docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "  Restart services: docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo "  Scale API: docker-compose -f $DOCKER_COMPOSE_FILE up -d --scale rethinking-park-api=2"
    echo
}

# Main deployment process
main() {
    log "Starting staging deployment process..."
    
    check_prerequisites
    validate_environment
    deploy_services
    wait_for_services
    run_staging_tests
    show_staging_info
    
    success "🎉 Staging deployment completed successfully!"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log "Stopping staging services..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
        success "Staging services stopped"
        ;;
    "restart")
        log "Restarting staging services..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" restart
        success "Staging services restarted"
        ;;
    "logs")
        docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
        ;;
    "status")
        docker-compose -f "$DOCKER_COMPOSE_FILE" ps
        ;;
    "test")
        run_staging_tests
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|test}"
        echo
        echo "Commands:"
        echo "  deploy  - Deploy the staging environment (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - Show service logs"
        echo "  status  - Show service status"
        echo "  test    - Run staging tests"
        exit 1
        ;;
esac