#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Master deployment script for OSCAR system
# Deploys all components with comprehensive dependency management

set -e

echo "🚀 OSCAR Complete System Deployment with Dependencies"
echo "======================================================"

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
required_vars=("SLACK_BOT_TOKEN" "SLACK_SIGNING_SECRET" "OSCAR_BEDROCK_AGENT_ID" "AWS_REGION")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

echo "🌍 Using AWS Region: $AWS_REGION"

# Function to check if pip is available and working
check_pip() {
    if ! command -v pip &> /dev/null; then
        echo "❌ pip is not installed. Please install pip first."
        exit 1
    fi
    
    if ! pip --version &> /dev/null; then
        echo "❌ pip is not working properly. Please check your Python installation."
        exit 1
    fi
    
    echo "✅ pip is available: $(pip --version)"
}

# Function to install dependencies for a directory
install_dependencies() {
    local dir=$1
    local temp_dir=$2
    local requirements_file="$dir/requirements.txt"
    
    if [ -f "$requirements_file" ]; then
        echo "📦 Installing dependencies from $requirements_file..."
        
        # Try to install all dependencies at once
        if ! pip install -r "$requirements_file" -t "$temp_dir/" --upgrade --quiet; then
            echo "⚠️  Batch installation failed, trying individual packages..."
            
            # Try installing each dependency individually
            while IFS= read -r line; do
                # Skip comments and empty lines
                if [[ $line =~ ^[a-zA-Z] ]]; then
                    echo "  Installing: $line"
                    if ! pip install "$line" -t "$temp_dir/" --upgrade --quiet; then
                        echo "❌ Failed to install $line"
                        return 1
                    fi
                fi
            done < "$requirements_file"
        fi
        
        echo "✅ Dependencies installed successfully"
    else
        echo "⚠️  No requirements.txt found in $dir"
    fi
}

# Function to verify critical dependencies
verify_dependencies() {
    local temp_dir=$1
    local deps=("${@:2}")
    
    echo "🔍 Verifying dependencies..."
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if [ ! -d "$temp_dir/$dep" ] && [ ! -d "$temp_dir/${dep//_/-}" ]; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "❌ Missing dependencies: ${missing_deps[*]}"
        return 1
    fi
    
    echo "✅ All dependencies verified"
    return 0
}

# Check pip availability
check_pip

echo ""
echo "1️⃣  Setting up DynamoDB tables..."
echo "=================================="
python setup_dynamodb_tables.py

echo ""
echo "2️⃣  Deploying Metrics Lambda Functions..."
echo "========================================="
./deploy_metrics.sh

echo ""
echo "3️⃣  Deploying OSCAR Main Agent..."
echo "================================="
./deploy_oscar_agent.sh

echo ""
echo "4️⃣  Deploying Communication Handler..."
echo "====================================="
./deploy_communication_handler.sh

echo ""
echo "🎉 Complete OSCAR System Deployment Finished!"
echo "=============================================="
echo ""
echo "📋 Deployed Components:"
echo "   ✅ DynamoDB tables (oscar-agent-context, oscar-agent-sessions)"
echo "   ✅ Metrics Lambda functions (4 functions)"
echo "   ✅ OSCAR Main Agent Lambda function"
echo "   ✅ Communication Handler Lambda function"
echo ""
echo "📝 Next Steps:"
echo "   1. Configure API Gateway for Slack webhook"
echo "   2. Update Slack app with webhook URL"
echo "   3. Configure Bedrock agent action groups"
echo "   4. Test with: @oscar hello"
echo ""
echo "🔍 Verification Commands:"
echo "   # Test main agent"
echo "   aws lambda invoke --function-name oscar-supervisor-agent --payload '{\"test\": \"connectivity\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json"
echo ""
echo "   # Test metrics agent"
echo "   aws lambda invoke --function-name oscar-test-metrics-agent-new --payload '{\"function\": \"test_basic\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json"
echo ""
echo "   # Test communication handler"
echo "   aws lambda invoke --function-name oscar-communication-handler --payload '{\"actionGroup\": \"test\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json"
echo ""
echo "📖 For detailed configuration, see: OSCAR_MASTER_DOCUMENTATION.md"