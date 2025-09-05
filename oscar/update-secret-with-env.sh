#!/bin/bash

# Update Secrets Manager secret with complete .env file content
# This script reads the .env file and updates the Secrets Manager secret with all values

set -e

# Configuration
AWS_REGION="us-east-1"
CDK_DIR="cdk"
ENV_FILE="$CDK_DIR/.env"
ENVIRONMENT="${ENVIRONMENT:-dev}"
SECRET_NAME="oscar-central-env-${ENVIRONMENT}-cdk"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Read .env file content as plain text (same format as main secret)
read_env_content() {
    local env_file=$1
    
    log_info "Reading .env file content..." >&2
    
    # Simply read the file content as-is (plain text format like main secret)
    if [[ -f "$env_file" ]]; then
        cat "$env_file"
    else
        log_error "File not found: $env_file" >&2
        return 1
    fi
}

# Update Secrets Manager secret
update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    log_info "Updating Secrets Manager secret: $secret_name"
    
    # Update the secret value
    aws secretsmanager update-secret \
        --region "$AWS_REGION" \
        --secret-id "$secret_name" \
        --secret-string "$secret_value" \
        --description "OSCAR central environment variables (updated $(date))" \
        > /dev/null
    
    log_success "Secret updated successfully!"
}

# Create secret if it doesn't exist
create_secret_if_needed() {
    local secret_name=$1
    
    log_info "Checking if secret exists: $secret_name"
    
    if aws secretsmanager describe-secret \
        --region "$AWS_REGION" \
        --secret-id "$secret_name" \
        > /dev/null 2>&1; then
        log_success "Secret exists and is accessible"
        return 0
    else
        log_warning "Secret does not exist: $secret_name"
        log_info "Creating secret: $secret_name"
        
        if aws secretsmanager create-secret \
            --region "$AWS_REGION" \
            --name "$secret_name" \
            --description "OSCAR central environment variables" \
            > /dev/null 2>&1; then
            log_success "Created secret: $secret_name"
            return 0
        else
            log_error "Failed to create secret: $secret_name"
            return 1
        fi
    fi
}

# Main function
main() {
    log_info "🔐 Updating Secrets Manager with complete .env content..."
    log_info "======================================================="
    
    # Check if .env file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error ".env file not found: $ENV_FILE"
        exit 1
    fi
    
    # Create secret if needed
    if ! create_secret_if_needed "$SECRET_NAME"; then
        exit 1
    fi
    
    # Read .env content as plain text (same format as main secret)
    log_info "Reading .env file: $ENV_FILE"
    local env_content=$(read_env_content "$ENV_FILE")
    
    if [[ -z "$env_content" ]]; then
        log_error "Failed to read .env file or file is empty"
        exit 1
    fi
    
    local var_count=$(echo "$env_content" | grep -c '^[A-Z]' || echo "0")
    log_info "Read .env content with $var_count environment variables"
    
    # Update the secret
    update_secret "$SECRET_NAME" "$env_content"
    
    # Verify the update
    log_info "Verifying secret update..."
    local stored_content=$(aws secretsmanager get-secret-value \
        --region "$AWS_REGION" \
        --secret-id "$SECRET_NAME" \
        --query "SecretString" \
        --output text)
    
    local stored_var_count=$(echo "$stored_content" | grep -c '^[A-Z]' || echo "0")
    log_success "✅ Secret updated successfully with $stored_var_count environment variables!"
    log_info "📁 Source file: $ENV_FILE"
    log_info "🔐 Secret name: $SECRET_NAME"
    log_info "🌍 Region: $AWS_REGION"
}

# Run main function
main "$@"