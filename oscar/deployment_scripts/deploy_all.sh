#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# OSCAR Complete Deployment Script
# Deploys all infrastructure and Lambda functions with proper dependencies and permissions

set -e

echo "🚀 OSCAR Complete Deployment Starting..."
echo "========================================"

# Load environment variables
if [ -f .env ]; then
    set -a  # automatically export all variables
    source .env
    set +a  # turn off automatic export
    echo "✅ Loaded environment variables from .env"
else
    echo "❌ .env file not found. Please create it with required variables."
    exit 1
fi

# Validate required environment variables
required_vars=("SLACK_BOT_TOKEN" "AWS_REGION" "OSCAR_BEDROCK_AGENT_ID")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

echo ""
echo "📋 Deployment Configuration:"
echo "   AWS Region: $AWS_REGION"
echo "   Bedrock Agent ID: $OSCAR_BEDROCK_AGENT_ID"
echo ""

# Step 1: Deploy CDK Infrastructure
echo "🏗️  Step 1: Deploying CDK Infrastructure..."
echo "============================================"
cd cdk
npm install --silent 2>/dev/null || echo "NPM packages already installed"
cdk bootstrap --region $AWS_REGION 2>/dev/null || echo "CDK already bootstrapped"
cdk deploy --require-approval never --region $AWS_REGION
cd ..
echo "✅ CDK Infrastructure deployed"

# Step 2: Setup DynamoDB Tables
echo ""
echo "🗄️  Step 2: Setting up DynamoDB Tables..."
echo "========================================="
python cdk/setup_dynamodb_tables.py
echo "✅ DynamoDB tables configured"

# Step 3: Deploy Lambda Functions
echo ""
echo "📦 Step 3: Deploying Lambda Functions..."
echo "======================================="

# Deploy metrics functions
echo "📊 Deploying Metrics Lambda Functions..."
./deployment_scripts/deploy_metrics.sh

# Deploy communication handler
echo "💬 Deploying Communication Handler..."
./deployment_scripts/deploy_communication_handler.sh

# Deploy main OSCAR agent
echo "🤖 Deploying OSCAR Main Agent..."
./deployment_scripts/deploy_oscar_agent.sh

echo ""
echo "🎉 OSCAR Complete Deployment Finished!"
echo "====================================="
echo ""
echo "📋 Deployment Summary:"
echo "   ✅ CDK Infrastructure"
echo "   ✅ DynamoDB Tables (oscar-agent-context, oscar-agent-sessions)"
echo "   ✅ Metrics Lambda Functions (4)"
echo "   ✅ Communication Handler"
echo "   ✅ OSCAR Main Agent"
echo ""
echo "📝 Next Steps:"
echo "   1. Configure Slack webhook URL in your Slack app"
echo "   2. Test OSCAR with: @oscar hello"
echo "   3. Monitor CloudWatch logs for any issues"
echo ""
echo "🔗 Useful Commands:"
echo "   Update only code: ./lambda_update_scripts/update_all.sh"
echo "   Update metrics: ./lambda_update_scripts/update_metrics.sh"
echo "   Update slack agent: ./lambda_update_scripts/update_slack_agent.sh"