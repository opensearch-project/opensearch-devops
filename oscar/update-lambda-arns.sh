#!/bin/bash

# Update Lambda ARNs in Agent Configurations
# This script updates the Lambda ARNs in agent configuration files with CDK-deployed Lambda functions

set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="395380602281"

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

# Check if Lambda function exists
check_lambda_exists() {
    local function_name=$1
    if aws lambda get-function --region "$AWS_REGION" --function-name "$function_name" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Update Lambda ARN in agent configuration
update_agent_lambda_arn() {
    local agent_name=$1
    local lambda_function_name=$2
    local config_file="agent-configs/$agent_name/agent-config.json"
    
    log_info "Updating Lambda ARNs for $agent_name agent..."
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi
    
    if ! check_lambda_exists "$lambda_function_name"; then
        log_error "Lambda function $lambda_function_name does not exist"
        return 1
    fi
    
    local lambda_arn="arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:$lambda_function_name"
    
    # Update the Lambda ARN in action groups
    jq --arg arn "$lambda_arn" '
        .actionGroups[] |= (
            if .actionGroupExecutor.lambda then
                .actionGroupExecutor.lambda = $arn
            else
                .
            end
        )
    ' "$config_file" > "${config_file}.tmp" && mv "${config_file}.tmp" "$config_file"
    
    log_success "Updated $agent_name agent Lambda ARN: $lambda_arn"
}

# Update communication Lambda ARN for privileged agent
update_communication_lambda_arn() {
    local config_file="agent-configs/oscar-privileged/agent-config.json"
    local lambda_function_name="oscar-communication-handler-cdk"
    
    log_info "Updating communication Lambda ARN for oscar-privileged agent..."
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi
    
    if ! check_lambda_exists "$lambda_function_name"; then
        log_error "Lambda function $lambda_function_name does not exist"
        return 1
    fi
    
    local lambda_arn="arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:$lambda_function_name"
    
    # Update the communication Lambda ARN specifically
    jq --arg arn "$lambda_arn" '
        .actionGroups[] |= (
            if .actionGroupName == "communication-orchestration" then
                .actionGroupExecutor.lambda = $arn
            else
                .
            end
        )
    ' "$config_file" > "${config_file}.tmp" && mv "${config_file}.tmp" "$config_file"
    
    log_success "Updated communication Lambda ARN: $lambda_arn"
}

# Main function
main() {
    log_info "🔄 Updating Lambda ARNs in agent configurations..."
    log_info "================================================"
    
    # Update Jenkins agent
    update_agent_lambda_arn "jenkins" "oscar-jenkins-agent-cdk"
    
    # Update metrics agents
    update_agent_lambda_arn "build-metrics" "oscar-build-metrics-agent-cdk"
    update_agent_lambda_arn "test-metrics" "oscar-test-metrics-agent-cdk"
    update_agent_lambda_arn "release-metrics" "oscar-release-metrics-agent-cdk"
    
    # Update supervisor agents (both use the same Lambda)
    update_agent_lambda_arn "oscar-limited" "oscar-supervisor-agent-cdk"
    update_agent_lambda_arn "oscar-privileged" "oscar-supervisor-agent-cdk"
    
    # Update communication Lambda for privileged agent
    update_communication_lambda_arn
    
    log_success "✅ All Lambda ARNs updated successfully!"
}

# Run main function
main "$@"