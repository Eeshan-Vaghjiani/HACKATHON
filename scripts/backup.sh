#!/bin/bash

# ============================================================================
# HABITATCANVAS DATABASE BACKUP SCRIPT
# ============================================================================
# This script creates automated backups of the PostgreSQL database
# and uploads them to S3 for long-term storage.

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="/backups"
LOG_FILE="/var/log/backup.log"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="habitatcanvas_backup_${DATE}.sql.gz"

# Default values (can be overridden by environment variables)
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-habitatcanvas}
POSTGRES_USER=${POSTGRES_USER:-habitatcanvas_user}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check required environment variables
check_env() {
    local required_vars=(
        "POSTGRES_PASSWORD"
        "S3_BUCKET"
        "AWS_ACCESS_KEY_ID"
        "AWS_SECRET_ACCESS_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error_exit "Required environment variable $var is not set"
        fi
    done
}

# Install required tools
install_tools() {
    log "Installing required tools..."
    
    # Install AWS CLI if not present
    if ! command -v aws &> /dev/null; then
        apk add --no-cache aws-cli
    fi
    
    # Install gzip if not present
    if ! command -v gzip &> /dev/null; then
        apk add --no-cache gzip
    fi
}

# Create backup directory
setup_backup_dir() {
    log "Setting up backup directory..."
    mkdir -p "$BACKUP_DIR"
    chmod 755 "$BACKUP_DIR"
}

# Test database connection
test_db_connection() {
    log "Testing database connection..."
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    if ! pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"; then
        error_exit "Cannot connect to database"
    fi
    
    log "Database connection successful"
}

# Create database backup
create_backup() {
    log "Creating database backup..."
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Create backup with compression
    pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --verbose \
        --no-owner \
        --no-privileges \
        --format=custom \
        --compress=9 \
        | gzip > "$BACKUP_DIR/$BACKUP_FILE"
    
    if [[ $? -eq 0 ]]; then
        log "Backup created successfully: $BACKUP_FILE"
        
        # Get backup file size
        local backup_size=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
        log "Backup size: $backup_size"
    else
        error_exit "Failed to create database backup"
    fi
}

# Upload backup to S3
upload_to_s3() {
    log "Uploading backup to S3..."
    
    local s3_path="s3://$S3_BUCKET/database-backups/$BACKUP_FILE"
    
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "$s3_path" \
        --storage-class STANDARD_IA \
        --metadata "created=$(date -Iseconds),database=$POSTGRES_DB,host=$POSTGRES_HOST"
    
    if [[ $? -eq 0 ]]; then
        log "Backup uploaded successfully to $s3_path"
    else
        error_exit "Failed to upload backup to S3"
    fi
}

# Clean up old local backups
cleanup_local_backups() {
    log "Cleaning up old local backups..."
    
    # Remove local backups older than 7 days
    find "$BACKUP_DIR" -name "habitatcanvas_backup_*.sql.gz" -mtime +7 -delete
    
    log "Local backup cleanup completed"
}

# Clean up old S3 backups
cleanup_s3_backups() {
    log "Cleaning up old S3 backups..."
    
    # List and delete backups older than retention period
    local cutoff_date=$(date -d "$BACKUP_RETENTION_DAYS days ago" +%Y%m%d)
    
    aws s3 ls "s3://$S3_BUCKET/database-backups/" | while read -r line; do
        local backup_date=$(echo "$line" | grep -o 'habitatcanvas_backup_[0-9]\{8\}' | cut -d'_' -f3)
        
        if [[ -n "$backup_date" && "$backup_date" < "$cutoff_date" ]]; then
            local old_backup=$(echo "$line" | awk '{print $4}')
            log "Deleting old backup: $old_backup"
            aws s3 rm "s3://$S3_BUCKET/database-backups/$old_backup"
        fi
    done
    
    log "S3 backup cleanup completed"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    # Test that the backup file can be read
    if gzip -t "$BACKUP_DIR/$BACKUP_FILE"; then
        log "Backup file integrity verified"
    else
        error_exit "Backup file is corrupted"
    fi
    
    # Optional: Test restore to a temporary database
    # This would require additional setup and resources
}

# Send notification
send_notification() {
    local status=$1
    local message=$2
    
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local color="good"
        if [[ "$status" == "error" ]]; then
            color="danger"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"attachments\":[{\"color\":\"$color\",\"text\":\"HabitatCanvas Backup: $message\"}]}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    log "Notification sent: $message"
}

# Main backup function
main() {
    log "Starting HabitatCanvas database backup process..."
    
    # Check prerequisites
    check_env
    install_tools
    setup_backup_dir
    
    # Perform backup
    test_db_connection
    create_backup
    verify_backup
    upload_to_s3
    
    # Cleanup
    cleanup_local_backups
    cleanup_s3_backups
    
    log "Backup process completed successfully"
    send_notification "success" "Database backup completed successfully: $BACKUP_FILE"
}

# Error handling wrapper
run_with_error_handling() {
    if ! main "$@"; then
        local exit_code=$?
        send_notification "error" "Database backup failed with exit code $exit_code"
        exit $exit_code
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_with_error_handling "$@"
fi