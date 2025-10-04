#!/bin/bash

# ============================================================================
# HABITATCANVAS PRODUCTION DEPLOYMENT SCRIPT
# ============================================================================
# This script handles the deployment of HabitatCanvas to production
# with zero-downtime blue-green deployment strategy.

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/deploy.log"
DATE=$(date +%Y%m%d_%H%M%S)

# Default values
ENVIRONMENT=${ENVIRONMENT:-production}
DEPLOYMENT_STRATEGY=${DEPLOYMENT_STRATEGY:-blue-green}
HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-300}
ROLLBACK_ON_FAILURE=${ROLLBACK_ON_FAILURE:-true}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}INFO:${NC} $1"
}

log_success() {
    log "${GREEN}SUCCESS:${NC} $1"
}

log_warning() {
    log "${YELLOW}WARNING:${NC} $1"
}

log_error() {
    log "${RED}ERROR:${NC} $1"
}

# Error handling
error_exit() {
    log_error "$1"
    send_notification "error" "Deployment failed: $1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "curl" "jq")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error_exit "Required command not found: $cmd"
        fi
    done
    
    # Check environment file
    if [[ ! -f "$PROJECT_ROOT/.env.production" ]]; then
        error_exit "Production environment file not found: .env.production"
    fi
    
    # Load environment variables
    source "$PROJECT_ROOT/.env.production"
    
    # Check required environment variables
    local required_vars=("FRONTEND_TAG" "BACKEND_TAG" "POSTGRES_PASSWORD" "SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error_exit "Required environment variable not set: $var"
        fi
    done
    
    log_success "Prerequisites check passed"
}

# Pull latest images
pull_images() {
    log_info "Pulling latest container images..."
    
    local images=(
        "ghcr.io/habitatcanvas/frontend:${FRONTEND_TAG}"
        "ghcr.io/habitatcanvas/backend:${BACKEND_TAG}"
    )
    
    for image in "${images[@]}"; do
        log_info "Pulling $image..."
        if ! docker pull "$image"; then
            error_exit "Failed to pull image: $image"
        fi
    done
    
    log_success "All images pulled successfully"
}

# Health check function
health_check() {
    local service_url=$1
    local timeout=${2:-60}
    local interval=5
    local elapsed=0
    
    log_info "Performing health check for $service_url..."
    
    while [[ $elapsed -lt $timeout ]]; do
        if curl -f -s "$service_url/health" > /dev/null 2>&1; then
            log_success "Health check passed for $service_url"
            return 0
        fi
        
        sleep $interval
        elapsed=$((elapsed + interval))
        log_info "Health check attempt $((elapsed / interval))..."
    done
    
    log_error "Health check failed for $service_url after ${timeout}s"
    return 1
}

# Database migration
run_migrations() {
    log_info "Running database migrations..."
    
    # Run migrations in a temporary container
    docker run --rm \
        --network habitatcanvas_habitatcanvas-network \
        -e DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}" \
        "ghcr.io/habitatcanvas/backend:${BACKEND_TAG}" \
        alembic upgrade head
    
    if [[ $? -eq 0 ]]; then
        log_success "Database migrations completed"
    else
        error_exit "Database migrations failed"
    fi
}

# Blue-green deployment
deploy_blue_green() {
    log_info "Starting blue-green deployment..."
    
    # Determine current and new environments
    local current_env="blue"
    local new_env="green"
    
    # Check which environment is currently active
    if docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" ps | grep -q "green"; then
        current_env="green"
        new_env="blue"
    fi
    
    log_info "Current environment: $current_env, deploying to: $new_env"
    
    # Deploy to new environment
    log_info "Deploying to $new_env environment..."
    
    # Update docker-compose file for new environment
    export COMPOSE_PROJECT_NAME="habitatcanvas-${new_env}"
    
    # Start new environment
    docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" up -d
    
    # Wait for services to be ready
    sleep 30
    
    # Health checks
    local backend_url="http://localhost:8000"
    local frontend_url="http://localhost"
    
    if ! health_check "$backend_url" "$HEALTH_CHECK_TIMEOUT"; then
        error_exit "Backend health check failed in $new_env environment"
    fi
    
    if ! health_check "$frontend_url" "$HEALTH_CHECK_TIMEOUT"; then
        error_exit "Frontend health check failed in $new_env environment"
    fi
    
    # Switch traffic to new environment
    log_info "Switching traffic to $new_env environment..."
    
    # Update load balancer configuration (implementation depends on your setup)
    # This could be updating nginx config, AWS ALB target groups, etc.
    switch_traffic_to_environment "$new_env"
    
    # Verify traffic switch
    sleep 10
    if ! health_check "$backend_url" 30; then
        error_exit "Traffic switch verification failed"
    fi
    
    # Stop old environment
    log_info "Stopping $current_env environment..."
    export COMPOSE_PROJECT_NAME="habitatcanvas-${current_env}"
    docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" down
    
    log_success "Blue-green deployment completed successfully"
}

# Rolling deployment
deploy_rolling() {
    log_info "Starting rolling deployment..."
    
    # Update services one by one
    local services=("backend" "frontend")
    
    for service in "${services[@]}"; do
        log_info "Updating $service..."
        
        # Update the service
        docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" up -d "$service"
        
        # Wait for service to be ready
        sleep 30
        
        # Health check
        case $service in
            "backend")
                health_check "http://localhost:8000" 60 || error_exit "$service health check failed"
                ;;
            "frontend")
                health_check "http://localhost" 60 || error_exit "$service health check failed"
                ;;
        esac
        
        log_success "$service updated successfully"
    done
    
    log_success "Rolling deployment completed successfully"
}

# Switch traffic (placeholder - implement based on your infrastructure)
switch_traffic_to_environment() {
    local env=$1
    log_info "Switching traffic to $env environment..."
    
    # Example implementations:
    
    # For nginx:
    # sed -i "s/upstream backend.*/upstream backend { server habitatcanvas-${env}-backend:8000; }/" /etc/nginx/nginx.conf
    # nginx -s reload
    
    # For AWS ALB:
    # aws elbv2 modify-target-group --target-group-arn $TARGET_GROUP_ARN --targets Id=habitatcanvas-${env}-backend
    
    # For Kubernetes:
    # kubectl patch service habitatcanvas-backend -p '{"spec":{"selector":{"version":"'$env'"}}}'
    
    log_success "Traffic switched to $env environment"
}

# Rollback function
rollback() {
    log_warning "Initiating rollback..."
    
    # Get previous image tags from backup
    local backup_file="/tmp/deployment_backup_${DATE}.env"
    
    if [[ -f "$backup_file" ]]; then
        source "$backup_file"
        
        # Rollback to previous images
        export FRONTEND_TAG="$PREVIOUS_FRONTEND_TAG"
        export BACKEND_TAG="$PREVIOUS_BACKEND_TAG"
        
        log_info "Rolling back to frontend:$FRONTEND_TAG, backend:$BACKEND_TAG"
        
        # Redeploy with previous images
        docker-compose -f "$PROJECT_ROOT/docker-compose.production.yml" up -d
        
        # Health checks
        if health_check "http://localhost:8000" 60 && health_check "http://localhost" 60; then
            log_success "Rollback completed successfully"
        else
            error_exit "Rollback failed - manual intervention required"
        fi
    else
        error_exit "Backup file not found - cannot rollback automatically"
    fi
}

# Backup current deployment state
backup_current_state() {
    log_info "Backing up current deployment state..."
    
    local backup_file="/tmp/deployment_backup_${DATE}.env"
    
    # Save current image tags
    cat > "$backup_file" << EOF
PREVIOUS_FRONTEND_TAG=${FRONTEND_TAG}
PREVIOUS_BACKEND_TAG=${BACKEND_TAG}
BACKUP_DATE=${DATE}
EOF
    
    log_success "Current state backed up to $backup_file"
}

# Send notification
send_notification() {
    local status=$1
    local message=$2
    
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local color="good"
        local emoji="✅"
        
        if [[ "$status" == "error" ]]; then
            color="danger"
            emoji="❌"
        elif [[ "$status" == "warning" ]]; then
            color="warning"
            emoji="⚠️"
        fi
        
        local payload=$(cat << EOF
{
    "attachments": [{
        "color": "$color",
        "text": "$emoji HabitatCanvas Deployment: $message",
        "fields": [
            {
                "title": "Environment",
                "value": "$ENVIRONMENT",
                "short": true
            },
            {
                "title": "Frontend Tag",
                "value": "$FRONTEND_TAG",
                "short": true
            },
            {
                "title": "Backend Tag",
                "value": "$BACKEND_TAG",
                "short": true
            },
            {
                "title": "Timestamp",
                "value": "$(date -Iseconds)",
                "short": true
            }
        ]
    }]
}
EOF
        )
        
        curl -X POST -H 'Content-type: application/json' \
            --data "$payload" \
            "$SLACK_WEBHOOK_URL" || true
    fi
}

# Smoke tests
run_smoke_tests() {
    log_info "Running smoke tests..."
    
    local tests_passed=0
    local tests_total=0
    
    # Test 1: API health endpoint
    ((tests_total++))
    if curl -f -s "http://localhost:8000/health" | jq -e '.status == "healthy"' > /dev/null; then
        ((tests_passed++))
        log_success "✓ API health check passed"
    else
        log_error "✗ API health check failed"
    fi
    
    # Test 2: Frontend accessibility
    ((tests_total++))
    if curl -f -s "http://localhost" | grep -q "HabitatCanvas"; then
        ((tests_passed++))
        log_success "✓ Frontend accessibility test passed"
    else
        log_error "✗ Frontend accessibility test failed"
    fi
    
    # Test 3: Database connectivity
    ((tests_total++))
    if curl -f -s "http://localhost:8000/api/health/db" | jq -e '.database == "connected"' > /dev/null; then
        ((tests_passed++))
        log_success "✓ Database connectivity test passed"
    else
        log_error "✗ Database connectivity test failed"
    fi
    
    # Test 4: Redis connectivity
    ((tests_total++))
    if curl -f -s "http://localhost:8000/api/health/redis" | jq -e '.redis == "connected"' > /dev/null; then
        ((tests_passed++))
        log_success "✓ Redis connectivity test passed"
    else
        log_error "✗ Redis connectivity test failed"
    fi
    
    log_info "Smoke tests completed: $tests_passed/$tests_total passed"
    
    if [[ $tests_passed -eq $tests_total ]]; then
        log_success "All smoke tests passed"
        return 0
    else
        log_error "Some smoke tests failed"
        return 1
    fi
}

# Main deployment function
main() {
    log_info "Starting HabitatCanvas deployment to $ENVIRONMENT..."
    
    # Trap errors for rollback
    if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
        trap 'rollback' ERR
    fi
    
    # Pre-deployment steps
    check_prerequisites
    backup_current_state
    pull_images
    run_migrations
    
    # Deployment
    case "$DEPLOYMENT_STRATEGY" in
        "blue-green")
            deploy_blue_green
            ;;
        "rolling")
            deploy_rolling
            ;;
        *)
            error_exit "Unknown deployment strategy: $DEPLOYMENT_STRATEGY"
            ;;
    esac
    
    # Post-deployment verification
    run_smoke_tests
    
    log_success "Deployment completed successfully!"
    send_notification "success" "Deployment completed successfully to $ENVIRONMENT"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi