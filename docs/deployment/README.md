# Deployment Guide

This guide covers deployment of the Rethinking Park Backend API across different environments.

## Overview

The project supports multiple deployment environments:

- **Local**: Quick local development setup
- **Development**: Full development environment with debugging features
- **Staging**: Production-like environment for testing
- **Production**: Optimized production deployment

## Quick Start

### Local Development (Simplest)

```bash
# Using default docker-compose.yml
docker-compose up --build

# Or using the script runner
./scripts/run.sh deployment deploy_dev.sh
```

### Development Environment

```bash
# Using development configuration
docker-compose -f deployment/docker-compose.dev.yml up --build

# Or using the deployment script
./scripts/run.sh deployment deploy_dev.sh
```

### Staging Environment

```bash
# Using staging configuration
docker-compose -f deployment/docker-compose.staging.yml up --build

# Or using the deployment script
./scripts/run.sh deployment deploy_staging.sh
```

### Production Environment

```bash
# Using production configuration
docker-compose -f deployment/production.yml up --build

# Or using the deployment script
./scripts/run.sh deployment deploy_production.sh
```

## Environment Configurations

### Local Development
- **File**: `docker-compose.yml`
- **Config**: `config/local.env`
- **Features**: Basic setup, uses host Redis, permissive CORS
- **Ports**: API (8000)

### Development Environment
- **File**: `deployment/docker-compose.dev.yml`
- **Config**: Auto-generated `.env.development`
- **Features**: Hot reload, debug port, Redis Commander UI, verbose logging
- **Ports**: API (8000), Debug (5678), Redis Commander (8081)

### Staging Environment
- **File**: `deployment/docker-compose.staging.yml`
- **Config**: `config/staging.env`
- **Features**: Production-like, monitoring, rate limiting, resource limits
- **Ports**: API (8000), Nginx (80/443), Prometheus (9090)

### Production Environment
- **File**: `deployment/production.yml`
- **Config**: `config/production.env`
- **Features**: Full monitoring, logging, security, performance optimization
- **Ports**: API (8000), Nginx (80/443), Prometheus (9090)

## Deployment Scripts

All deployment scripts are located in `scripts/deployment/`:

### Available Scripts

| Script | Environment | Description |
|--------|-------------|-------------|
| `deploy_dev.sh` | Development | Full dev environment with debugging |
| `deploy_staging.sh` | Staging | Production-like testing environment |
| `deploy_production.sh` | Production | Optimized production deployment |

### Script Usage

```bash
# Deploy environment
./scripts/run.sh deployment <script_name>

# Stop services
./scripts/run.sh deployment <script_name> stop

# Restart services
./scripts/run.sh deployment <script_name> restart

# View logs
./scripts/run.sh deployment <script_name> logs

# Check status
./scripts/run.sh deployment <script_name> status
```

### Examples

```bash
# Deploy development environment
./scripts/run.sh deployment deploy_dev.sh

# Stop production services
./scripts/run.sh deployment deploy_production.sh stop

# View staging logs
./scripts/run.sh deployment deploy_staging.sh logs
```

## Environment Variables

### Required Variables

All environments require these variables:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GCS_BUCKET_NAME=your-bucket-name
```

### Environment-Specific Variables

#### Development
```bash
DEBUG=true
LOG_LEVEL=DEBUG
RATE_LIMIT_ENABLED=false
```

#### Staging
```bash
DEBUG=false
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=120
```

#### Production
```bash
DEBUG=false
LOG_LEVEL=WARNING
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
ENABLE_HTTPS=true
```

## Service Architecture

### Development Environment
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Service   │    │  Redis Service  │    │ Redis Commander │
│   Port: 8000    │    │   Port: 6379    │    │   Port: 8081    │
│   Debug: 5678   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Staging/Production Environment
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Nginx Proxy    │    │   API Service   │    │  Redis Service  │
│  Port: 80/443   │    │   Port: 8000    │    │   Port: 6379    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │ Log Aggregator  │
│   Port: 9090    │    │  (Fluent Bit)   │
└─────────────────┘    └─────────────────┘
```

## Prerequisites

### System Requirements
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended for production)
- 10GB disk space

### Required Files
- `service-account-key.json` - Google Cloud service account key
- Environment configuration files (auto-generated for dev)

## Configuration Management

### Configuration Files Location
```
config/
├── local.env          # Local development
├── staging.env        # Staging environment  
└── production.env     # Production environment
```

### Docker Compose Files Location
```
deployment/
├── docker-compose.dev.yml      # Development
├── docker-compose.staging.yml  # Staging
└── production.yml              # Production
```

## Monitoring and Logging

### Available Endpoints

| Environment | Endpoint | Description |
|-------------|----------|-------------|
| All | `http://localhost:8000/health` | Basic health check |
| Staging/Prod | `http://localhost:8000/api/v1/health-detailed` | Detailed health |
| Staging/Prod | `http://localhost:8000/api/v1/metrics` | Application metrics |
| Staging/Prod | `http://localhost:9090` | Prometheus dashboard |
| Development | `http://localhost:8081` | Redis Commander |

### Log Access

```bash
# View all logs
docker-compose -f <compose-file> logs -f

# View specific service logs
docker-compose -f <compose-file> logs -f <service-name>

# Examples
docker-compose -f deployment/production.yml logs -f rethinking-park-api
docker-compose logs -f  # For local development
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status
docker-compose ps

# Check logs for errors
docker-compose logs <service-name>

# Restart specific service
docker-compose restart <service-name>
```

#### Port Conflicts
```bash
# Check what's using the port
sudo netstat -tulpn | grep :8000

# Stop conflicting services
sudo systemctl stop <service-name>
```

#### Permission Issues
```bash
# Fix file permissions
chmod +x scripts/deployment/*.sh
chmod 600 service-account-key.json
```

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check (staging/production)
curl http://localhost:8000/api/v1/health-detailed

# Check Redis connection
docker-compose exec redis redis-cli ping
```

## Security Considerations

### Production Security
- Use HTTPS with valid SSL certificates
- Restrict CORS origins to your domains
- Use strong passwords for Redis
- Regularly update Docker images
- Monitor access logs

### Environment Variables
- Never commit sensitive environment variables
- Use Docker secrets for production passwords
- Rotate service account keys regularly

## Performance Optimization

### Resource Limits
Each environment has appropriate resource limits:

- **Development**: Unlimited (for debugging)
- **Staging**: 1.5GB RAM, 0.8 CPU
- **Production**: 2GB RAM, 1.0 CPU

### Scaling

```bash
# Scale API service (staging/production)
docker-compose -f deployment/production.yml up -d --scale rethinking-park-api=3

# Scale with load balancer
# (Nginx automatically load balances multiple API instances)
```

## Backup and Recovery

### Database Backup
```bash
# Backup Redis data
docker-compose exec redis redis-cli BGSAVE

# Copy backup file
docker cp <container-id>:/data/dump.rdb ./backup/
```

### Configuration Backup
- Keep environment files in version control
- Backup service account keys securely
- Document any manual configuration changes

## Migration Between Environments

### From Development to Staging
1. Test all features in development
2. Update staging configuration
3. Deploy to staging
4. Run staging tests
5. Verify all endpoints work

### From Staging to Production
1. Complete staging testing
2. Update production configuration
3. Schedule maintenance window
4. Deploy to production
5. Monitor for issues
6. Rollback if necessary

## Support

For deployment issues:
1. Check the logs first
2. Verify configuration files
3. Test with curl commands
4. Check resource usage
5. Review this documentation

## Quick Reference

### Essential Commands
```bash
# Deploy development
./scripts/run.sh deployment deploy_dev.sh

# Deploy staging  
./scripts/run.sh deployment deploy_staging.sh

# Deploy production
./scripts/run.sh deployment deploy_production.sh

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```