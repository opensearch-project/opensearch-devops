#!/bin/bash

# Complete OSCAR Deployment Script
# Deploys infrastructure in the correct order and integrates all components

set -e

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

log_info "🚀 Starting Complete OSCAR Deployment"
log_info "====================================="

# Step 1: Deploy CDK Infrastructure Stacks (excluding agents and secrets)
log_info "📦 Step 1: Deploying CDK Infrastructure Stacks"
log_info "This includes: Permissions, Storage, Lambda, API Gateway"
log_info "Note: Secrets Manager will be deployed LAST after all agents are created"

cd cdk

# Load environment variables
if [ -f .env ]; then
    log_info "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
else
    log_error ".env file not found in cdk directory!"
    exit 1
fi

# Set CDK environment variables
export CDK_DEFAULT_ACCOUNT=$AWS_ACCOUNT_ID
export CDK_DEFAULT_REGION=$AWS_DEFAULT_REGION

# Lambda code will be deployed directly from source directories

log_info "Deploying CDK stacks in correct order..."

# Deploy in dependency order (Secrets Manager will be deployed LAST)
log_info "Deploying Permissions stack..."
# Check if roles exist and handle drift
if ! aws iam get-role --role-name oscar-lambda-execution-role-cdk >/dev/null 2>&1; then
    log_warning "IAM roles missing - checking for stack drift..."
    if aws cloudformation describe-stacks --stack-name OscarPermissionsStack >/dev/null 2>&1; then
        log_info "Permissions stack exists but roles are missing - deleting and recreating..."
        aws cloudformation delete-stack --stack-name OscarPermissionsStack
        log_info "Waiting for stack deletion..."
        aws cloudformation wait stack-delete-complete --stack-name OscarPermissionsStack
    fi
fi
cdk deploy OscarPermissionsStack --require-approval never

log_info "Deploying Storage stack..."
cdk deploy OscarStorageStack --require-approval never

log_info "Deploying Lambda stack (assets will be prepared automatically)..."
cdk deploy OscarLambdaStack --require-approval never

log_info "Deploying API Gateway stack..."
cdk deploy OscarApiGatewayStack --require-approval never

log_success "✅ CDK Infrastructure stacks deployed successfully!"

cd ..

# Step 2: Update Lambda ARNs in agent configurations
log_info "📝 Step 2: Updating Lambda ARNs in agent configurations"
log_info "Lambda functions have been deployed, now updating agent configurations with their ARNs"

# Wait for Lambda functions to be fully active
log_info "Waiting for Lambda functions to be active..."
sleep 10

./update-lambda-arns.sh

log_success "✅ Lambda ARNs updated in agent configurations"

# Step 3: Deploy agents using our proven manual deployment logic
log_info "🤖 Step 3: Deploying Bedrock Agents"
log_info "Using proven manual deployment logic with proper wait times and collaborator handling"

./deploy-all-agents.sh

log_success "✅ All agents deployed successfully with proper collaborator relationships!"

# Step 4: Update .env file with all CDK resource IDs
log_info "📝 Step 4: Updating .env file with CDK resource IDs"
log_info "This ensures all deployed resource IDs are captured before Secrets Manager deployment"

./update-cdk-env.sh

log_success "✅ .env file updated with all CDK resource IDs!"

# Step 5: Deploy Secrets Manager with all resource IDs (LAST)
log_info "🔐 Step 5: Deploying Secrets Manager with all resource IDs"
log_info "This is deployed LAST because it needs all agent IDs and resource ARNs"

cd cdk
log_info "Deploying Secrets Manager stack..."
cdk deploy OscarSecretsStack --require-approval never

log_success "✅ Secrets Manager stack deployed!"

cd ..

# Step 6: Update Secrets Manager with complete .env content
log_info "📝 Step 6: Updating Secrets Manager with complete .env content"
log_info "This populates the secret with all environment variables from the .env file"

./update-secret-with-env.sh

log_success "✅ Secrets Manager updated with complete environment configuration!"

# Step 7: Fix ALL OSCAR Permissions
log_info "🔐 Step 7: Fixing ALL OSCAR permissions (IAM roles + Lambda functions + Bedrock agents)"
log_info "This adds comprehensive identity-based and resource-based policies for complete functionality"

./oscar-permissions-fixer.sh

log_success "✅ All OSCAR permissions fixed!"

# Step 7.5: Cleanup Lambda assets to save disk space
log_info "🧹 Cleaning up Lambda assets to save disk space..."
rm -rf cdk/lambda_assets
log_success "✅ Lambda assets cleaned up!"

# Step 8: Final verification
log_info "🔍 Step 8: Final Integration Verification"

log_info "Verifying deployed resources..."

# Check agents
log_info "Checking deployed agents..."
aws bedrock-agent list-agents --query "agentSummaries[?contains(agentName, 'oscar') || contains(agentName, 'jenkins') || contains(agentName, 'metrics')].{Name:agentName,ID:agentId,Status:agentStatus}" --output table

# Check Lambda functions
log_info "Checking deployed Lambda functions..."
aws lambda list-functions --query "Functions[?contains(FunctionName, 'oscar')].{Name:FunctionName,Runtime:Runtime,State:State}" --output table

log_success "🎉 Complete OSCAR Deployment Finished Successfully!"
log_success "=============================================="

log_info "📋 Deployment Summary:"
log_info "✅ CDK Infrastructure: Permissions, Secrets, Storage, Lambda, API Gateway"
log_info "✅ Bedrock Agents: All agents with proper collaborator relationships"
log_info "✅ Lambda Integration: All action groups connected to Lambda functions"
log_info "✅ Environment Variables: .env file updated with all resource IDs"
log_info "✅ Secrets Manager: All resource IDs stored securely"

log_info "🧪 Next Steps:"
log_info "1. Test individual agents in AWS Bedrock console"
log_info "2. Test supervisor agents with collaborator routing"
log_info "3. Test Jenkins operations and metrics queries"
log_info "4. Verify end-to-end functionality"

log_info "📁 Key Files Updated:"
log_info "- cdk/.env: Contains all deployed resource IDs"
log_info "- deployed-agent-ids.json: Contains agent and alias IDs"
log_info "- Agent configurations: Updated with actual Lambda ARNs"