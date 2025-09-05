#!/bin/bash

# Update .env file with CDK-deployed resource IDs
# This script extracts resource IDs from deployed CDK stacks and updates the .env file

set -e

# Configuration
AWS_REGION="us-east-1"
CDK_DIR="cdk"
ENV_FILE="$CDK_DIR/.env"

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

# Update environment variable in .env file
update_env_var() {
    local var_name=$1
    local var_value=$2
    
    if [[ -z "$var_value" ]]; then
        log_warning "Empty value for $var_name, skipping..."
        return 0
    fi
    
    # Create backup
    cp "$ENV_FILE" "${ENV_FILE}.bak"
    
    # Update or add the variable
    if grep -q "^${var_name}=" "$ENV_FILE"; then
        # Variable exists, update it
        sed -i.tmp "s|^${var_name}=.*|${var_name}=${var_value}|" "$ENV_FILE"
        rm -f "${ENV_FILE}.tmp"
        log_info "Updated $var_name=$var_value"
    else
        # Variable doesn't exist, add it
        echo "${var_name}=${var_value}" >> "$ENV_FILE"
        log_info "Added $var_name=$var_value"
    fi
}

# Get CDK stack output
get_stack_output() {
    local stack_name=$1
    local output_key=$2
    
    aws cloudformation describe-stacks \
        --region "$AWS_REGION" \
        --stack-name "$stack_name" \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null || echo ""
}

# Get Lambda function ARN
get_lambda_arn() {
    local function_name=$1
    
    aws lambda get-function \
        --region "$AWS_REGION" \
        --function-name "$function_name" \
        --query "Configuration.FunctionArn" \
        --output text 2>/dev/null || echo ""
}

# Get DynamoDB table name
get_table_name() {
    local table_pattern=$1
    
    aws dynamodb list-tables \
        --region "$AWS_REGION" \
        --query "TableNames[?contains(@, '$table_pattern')]" \
        --output text 2>/dev/null || echo ""
}

# Get API Gateway URL
get_api_gateway_url() {
    local api_id=$(get_stack_output "OscarApiGatewayStack" "ApiGatewayId")
    if [[ -n "$api_id" ]]; then
        echo "https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com/prod"
    fi
}

# Update agent IDs from deployed-agent-ids.json
update_agent_ids() {
    local agent_ids_file="deployed-agent-ids.json"
    
    if [[ ! -f "$agent_ids_file" ]]; then
        log_warning "Agent IDs file not found: $agent_ids_file"
        return 0
    fi
    
    log_info "Updating agent IDs from deployment..."
    
    # Update Jenkins agent
    local jenkins_id=$(jq -r '.jenkins.agent_id // empty' "$agent_ids_file")
    local jenkins_alias=$(jq -r '.jenkins.alias_id // empty' "$agent_ids_file")
    if [[ -n "$jenkins_id" ]]; then
        update_env_var "JENKINS_AGENT_ID" "$jenkins_id"
        update_env_var "JENKINS_AGENT_ALIAS_ID" "$jenkins_alias"
    fi
    
    # Update Build Metrics agent
    local build_id=$(jq -r '."build-metrics".agent_id // empty' "$agent_ids_file")
    local build_alias=$(jq -r '."build-metrics".alias_id // empty' "$agent_ids_file")
    if [[ -n "$build_id" ]]; then
        update_env_var "BUILD_METRICS_AGENT_ID" "$build_id"
        update_env_var "BUILD_METRICS_AGENT_ALIAS_ID" "$build_alias"
    fi
    
    # Update Test Metrics agent
    local test_id=$(jq -r '."test-metrics".agent_id // empty' "$agent_ids_file")
    local test_alias=$(jq -r '."test-metrics".alias_id // empty' "$agent_ids_file")
    if [[ -n "$test_id" ]]; then
        update_env_var "TEST_METRICS_AGENT_ID" "$test_id"
        update_env_var "TEST_METRICS_AGENT_ALIAS_ID" "$test_alias"
    fi
    
    # Update Release Metrics agent
    local release_id=$(jq -r '."release-metrics".agent_id // empty' "$agent_ids_file")
    local release_alias=$(jq -r '."release-metrics".alias_id // empty' "$agent_ids_file")
    if [[ -n "$release_id" ]]; then
        update_env_var "RELEASE_METRICS_AGENT_ID" "$release_id"
        update_env_var "RELEASE_METRICS_AGENT_ALIAS_ID" "$release_alias"
    fi
    
    # Update OSCAR Limited agent
    local limited_id=$(jq -r '."oscar-limited".agent_id // empty' "$agent_ids_file")
    local limited_alias=$(jq -r '."oscar-limited".alias_id // empty' "$agent_ids_file")
    if [[ -n "$limited_id" ]]; then
        update_env_var "OSCAR_LIMITED_BEDROCK_AGENT_ID" "$limited_id"
        update_env_var "OSCAR_LIMITED_BEDROCK_AGENT_ALIAS_ID" "$limited_alias"
    fi
    
    # Update OSCAR Privileged agent
    local privileged_id=$(jq -r '."oscar-privileged".agent_id // empty' "$agent_ids_file")
    local privileged_alias=$(jq -r '."oscar-privileged".alias_id // empty' "$agent_ids_file")
    if [[ -n "$privileged_id" ]]; then
        update_env_var "OSCAR_PRIVILEGED_BEDROCK_AGENT_ID" "$privileged_id"
        update_env_var "OSCAR_PRIVILEGED_BEDROCK_AGENT_ALIAS_ID" "$privileged_alias"
    fi
}

# Main function
main() {
    log_info "🔄 Updating .env file with CDK-deployed resource IDs..."
    log_info "====================================================="
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error ".env file not found: $ENV_FILE"
        exit 1
    fi
    
    # Update Lambda function ARNs
    log_info "Updating Lambda function ARNs..."
    update_env_var "MAIN_LAMBDA_ARN" "$(get_lambda_arn 'oscar-supervisor-agent-cdk')"
    update_env_var "COMMUNICATION_LAMBDA_ARN" "$(get_lambda_arn 'oscar-communication-handler-cdk')"
    update_env_var "JENKINS_LAMBDA_ARN" "$(get_lambda_arn 'oscar-jenkins-agent-cdk')"
    update_env_var "BUILD_METRICS_LAMBDA_ARN" "$(get_lambda_arn 'oscar-build-metrics-agent-cdk')"
    update_env_var "TEST_METRICS_LAMBDA_ARN" "$(get_lambda_arn 'oscar-test-metrics-agent-cdk')"
    update_env_var "RELEASE_METRICS_LAMBDA_ARN" "$(get_lambda_arn 'oscar-release-metrics-agent-cdk')"
    
    # Update Lambda function names for metrics configuration
    log_info "Updating Lambda function names..."
    update_env_var "METRICS_TEST_FUNCTION" "oscar-test-metrics-agent-cdk"
    update_env_var "METRICS_BUILD_FUNCTION" "oscar-build-metrics-agent-cdk"
    update_env_var "METRICS_RELEASE_FUNCTION" "oscar-release-metrics-agent-cdk"
    update_env_var "METRICS_DEPLOYMENT_FUNCTION" "oscar-deployment-metrics-agent-cdk"
    update_env_var "JENKINS_LAMBDA_FUNCTION_NAME" "oscar-jenkins-agent-cdk"
    
    # Update all Lambda function names for dynamic usage
    update_env_var "MAIN_LAMBDA_FUNCTION_NAME" "oscar-supervisor-agent-cdk"
    update_env_var "COMMUNICATION_LAMBDA_FUNCTION_NAME" "oscar-communication-handler-cdk"
    
    # Update DynamoDB table names and ARNs
    log_info "Updating DynamoDB table names and ARNs..."
    local context_table=$(get_stack_output "OscarStorageStack" "ContextTableName")
    local sessions_table=$(get_stack_output "OscarStorageStack" "SessionsTableName")
    local context_table_arn=$(get_stack_output "OscarStorageStack" "ContextTableArn")
    local sessions_table_arn=$(get_stack_output "OscarStorageStack" "SessionsTableArn")
    
    if [[ -n "$context_table" ]]; then
        update_env_var "CONTEXT_TABLE_NAME" "$context_table"
    fi
    if [[ -n "$sessions_table" ]]; then
        update_env_var "SESSIONS_TABLE_NAME" "$sessions_table"
    fi
    if [[ -n "$context_table_arn" ]]; then
        update_env_var "CONTEXT_TABLE_ARN" "$context_table_arn"
    fi
    if [[ -n "$sessions_table_arn" ]]; then
        update_env_var "SESSIONS_TABLE_ARN" "$sessions_table_arn"
    fi
    
    # Update API Gateway resources
    log_info "Updating API Gateway resources..."
    local api_id=$(get_stack_output "OscarApiGatewayStack" "ApiGatewayId")
    local api_stage=$(get_stack_output "OscarApiGatewayStack" "ApiGatewayStage")
    local api_deployment_id=$(get_stack_output "OscarApiGatewayStack" "ApiGatewayDeploymentId")
    local api_url=$(get_api_gateway_url)
    
    if [[ -n "$api_id" ]]; then
        update_env_var "API_GATEWAY_ID" "$api_id"
    fi
    if [[ -n "$api_stage" ]]; then
        update_env_var "API_GATEWAY_STAGE" "$api_stage"
    fi
    if [[ -n "$api_deployment_id" ]]; then
        update_env_var "API_GATEWAY_DEPLOYMENT_ID" "$api_deployment_id"
    fi
    if [[ -n "$api_url" ]]; then
        update_env_var "API_GATEWAY_URL" "$api_url"
        update_env_var "SLACK_EVENTS_URL" "${api_url}/slack/events"
    fi
    
    # Update Secrets Manager secret name
    log_info "Updating Secrets Manager secret name..."
    local secret_arn=$(get_stack_output "OscarSecretsStack" "CentralEnvSecretArn")
    if [[ -n "$secret_arn" ]]; then
        local secret_name=$(echo "$secret_arn" | sed 's|.*:secret:\([^:]*\).*|\1|')
        update_env_var "CENTRAL_SECRET_NAME" "$secret_name"
    fi
    
    # Update IAM role names and ARNs
    log_info "Updating IAM role names and ARNs..."
    local lambda_role_arn=$(get_stack_output 'OscarPermissionsStack' 'LambdaExecutionRoleBaseArn')
    local bedrock_role_arn=$(get_stack_output 'OscarPermissionsStack' 'BedrockAgentRoleArn')
    local comm_role_arn=$(get_stack_output 'OscarPermissionsStack' 'LambdaExecutionRoleCommunicationArn')
    local jenkins_role_arn=$(get_stack_output 'OscarPermissionsStack' 'LambdaExecutionRoleJenkinsArn')
    local api_role_arn=$(get_stack_output 'OscarPermissionsStack' 'ApiGatewayRoleArn')
    
    # Update ARNs
    update_env_var "LAMBDA_EXECUTION_ROLE_ARN" "$lambda_role_arn"
    update_env_var "BEDROCK_AGENT_ROLE_ARN" "$bedrock_role_arn"
    update_env_var "COMMUNICATION_HANDLER_ROLE_ARN" "$comm_role_arn"
    update_env_var "JENKINS_LAMBDA_ROLE_ARN" "$jenkins_role_arn"
    update_env_var "API_GATEWAY_ROLE_ARN" "$api_role_arn"
    
    # Extract and update role names from ARNs
    if [[ -n "$lambda_role_arn" ]]; then
        local lambda_role_name=$(echo "$lambda_role_arn" | awk -F'/' '{print $NF}')
        update_env_var "LAMBDA_EXECUTION_ROLE_NAME" "$lambda_role_name"
    fi
    if [[ -n "$bedrock_role_arn" ]]; then
        local bedrock_role_name=$(echo "$bedrock_role_arn" | awk -F'/' '{print $NF}')
        update_env_var "BEDROCK_AGENT_ROLE_NAME" "$bedrock_role_name"
    fi
    if [[ -n "$comm_role_arn" ]]; then
        local comm_role_name=$(echo "$comm_role_arn" | awk -F'/' '{print $NF}')
        update_env_var "COMMUNICATION_HANDLER_ROLE_NAME" "$comm_role_name"
    fi
    if [[ -n "$jenkins_role_arn" ]]; then
        local jenkins_role_name=$(echo "$jenkins_role_arn" | awk -F'/' '{print $NF}')
        update_env_var "JENKINS_LAMBDA_ROLE_NAME" "$jenkins_role_name"
    fi
    if [[ -n "$api_role_arn" ]]; then
        local api_role_name=$(echo "$api_role_arn" | awk -F'/' '{print $NF}')
        update_env_var "API_GATEWAY_ROLE_NAME" "$api_role_name"
    fi
    
    # Update agent IDs from deployment
    update_agent_ids
    
    # Clean up backup if everything succeeded
    rm -f "${ENV_FILE}.bak"
    
    log_success "✅ .env file updated with all CDK resource IDs!"
    log_info "📁 Updated file: $ENV_FILE"
}

# Run main function
main "$@"