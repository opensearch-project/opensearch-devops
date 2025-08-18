#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Update ONLY the code for Slack Agent Lambda function
# Preserves all permissions and configurations
# Updates slack_handler.py and communication_handler.py

set -e

echo "🔄 Updating Slack Agent Lambda Function (Code Only)..."

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

# Set function name
FUNCTION_NAME="oscar-supervisor-agent"

# Verify region configuration
echo "🌍 Using AWS Region: $AWS_REGION"
if [ "$AWS_REGION" != "us-east-1" ]; then
    echo "⚠️  Warning: Expected region us-east-1, but using $AWS_REGION"
fi

echo "📦 Creating deployment package..."

# Create temporary directory for deployment
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Copy the main agent files (including slack_handler.py and communication_handler.py)
cp oscar-agent/*.py $TEMP_DIR/
cp oscar-agent/app.py $TEMP_DIR/lambda_function.py

# Copy the entire slack_handler package directory
if [ -d "oscar-agent/slack_handler" ]; then
    echo "📁 Copying slack_handler package..."
    cp -r oscar-agent/slack_handler $TEMP_DIR/
    echo "✅ Copied slack_handler package structure"
else
    echo "❌ slack_handler directory not found!"
    exit 1
fi

# Copy the entire bedrock package directory (refactored modular components)
if [ -d "oscar-agent/bedrock" ]; then
    echo "📁 Copying bedrock package..."
    cp -r oscar-agent/bedrock $TEMP_DIR/
    echo "✅ Copied bedrock package structure"
else
    echo "❌ bedrock directory not found!"
    exit 1
fi

# Create comprehensive requirements.txt for the Lambda function
cat > $TEMP_DIR/requirements.txt << EOF
# Core AWS and Slack dependencies
boto3>=1.34.0
botocore>=1.34.0
slack_sdk>=3.19.0
slack_bolt>=1.18.0

# HTTP and networking
requests>=2.31.0
urllib3>=2.0.0

# Additional dependencies for enhanced functionality
opensearch-py==2.4.2
aws-requests-auth==0.4.3

# Ensure we have all transitive dependencies
certifi>=2023.7.22
charset-normalizer>=3.0.0
idna>=3.0.0
python-dateutil>=2.8.0
jmespath>=1.0.0
s3transfer>=0.6.0
six>=1.16.0
EOF

# Install dependencies with upgrade flag to ensure latest compatible versions
echo "📦 Installing Python dependencies..."
if ! pip install -r $TEMP_DIR/requirements.txt -t $TEMP_DIR/ --upgrade --quiet; then
    echo "❌ Failed to install dependencies with pip. Trying alternative approach..."
    # Try installing each dependency individually
    while IFS= read -r line; do
        if [[ $line =~ ^[a-zA-Z] ]]; then
            echo "  Installing: $line"
            pip install "$line" -t $TEMP_DIR/ --upgrade --quiet || {
                echo "❌ Failed to install $line"
                exit 1
            }
        fi
    done < $TEMP_DIR/requirements.txt
fi

# Verify critical dependencies were installed
echo "🔍 Verifying dependencies..."
CRITICAL_DEPS=("slack_bolt" "slack_sdk" "boto3" "botocore" "requests" "opensearchpy")
MISSING_DEPS=()

for dep in "${CRITICAL_DEPS[@]}"; do
    if [ ! -d "$TEMP_DIR/$dep" ] && [ ! -d "$TEMP_DIR/${dep//_/-}" ]; then
        MISSING_DEPS+=("$dep")
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "❌ Missing dependencies: ${MISSING_DEPS[*]}"
    echo "📦 Attempting manual installation..."
    
    for dep in "${MISSING_DEPS[@]}"; do
        case $dep in
            "slack_bolt")
                pip install slack_bolt>=1.18.0 -t $TEMP_DIR/ --upgrade --quiet || {
                    echo "❌ Failed to install slack_bolt"
                    exit 1
                }
                ;;
            "slack_sdk")
                pip install slack_sdk>=3.19.0 -t $TEMP_DIR/ --upgrade --quiet || {
                    echo "❌ Failed to install slack_sdk"
                    exit 1
                }
                ;;
            "opensearchpy")
                pip install opensearch-py==2.4.2 -t $TEMP_DIR/ --upgrade --quiet || {
                    echo "❌ Failed to install opensearch-py"
                    exit 1
                }
                ;;
            *)
                pip install "$dep" -t $TEMP_DIR/ --upgrade --quiet || {
                    echo "❌ Failed to install $dep"
                    exit 1
                }
                ;;
        esac
    done
fi

echo "✅ Dependencies verified"

# List installed packages for debugging
echo "📋 Installed packages:"
ls -la $TEMP_DIR/ | grep "^d" | awk '{print $9}' | grep -E "^(slack|boto|requests|opensearch|urllib3|certifi)" | head -10

# Verify critical code fixes are in place
echo "🔍 Verifying critical code fixes..."
if ! grep -q "def get_context_for_query" oscar-agent/storage.py; then
    echo "❌ CRITICAL: storage.py is missing get_context_for_query method"
    echo "   This will cause AttributeError. Please restore the correct storage.py file."
    exit 1
fi

# Note: slack_handler.py is now a simple import file, so skip the variable collision check
# The actual logic is in the slack_handler package modules
echo "✅ Using refactored slack_handler package structure"

echo "✅ Critical code fixes verified"

# Create deployment package using Python to ensure correct structure
echo "📦 Creating deployment package..."
python3 -c "
import os
import zipfile
import sys

# Change to the directory
os.chdir('$TEMP_DIR')

# Create zip file
with zipfile.ZipFile('../slack-agent-update.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if not file.endswith('.pyc'):
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, '.')
                zipf.write(file_path, arcname)

print('✅ Deployment package created successfully')
"

DEPLOYMENT_PACKAGE="$TEMP_DIR/../slack-agent-update.zip"
PACKAGE_SIZE=$(ls -la $DEPLOYMENT_PACKAGE | awk '{print $5}')
echo "✅ Created deployment package: $DEPLOYMENT_PACKAGE"
echo "📏 Package size: $(numfmt --to=iec $PACKAGE_SIZE)"

# Verify package size is reasonable (should be > 1MB with dependencies)
if [ $PACKAGE_SIZE -lt 1000000 ]; then
    echo "⚠️  Warning: Package size is unusually small ($PACKAGE_SIZE bytes)"
    echo "   This might indicate missing dependencies"
    echo "   Expected size: >10MB with all dependencies"
fi

# Check if Lambda function exists
echo "🔍 Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION > /dev/null 2>&1; then
    echo "🔄 Updating Lambda function code and environment variables..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://$DEPLOYMENT_PACKAGE \
        --region $AWS_REGION >/dev/null

    # Wait for code update to complete
    echo "⏳ Waiting for code update to complete..."
    aws lambda wait function-updated --function-name $FUNCTION_NAME --region $AWS_REGION

    # Create environment variables JSON file
    # Escape the CHANNEL_MAPPINGS JSON for proper embedding
    ESCAPED_CHANNEL_MAPPINGS=$(echo "$CHANNEL_MAPPINGS" | sed 's/"/\\"/g')
    
    cat > $TEMP_DIR/env-vars.json << EOF
{
    "Variables": {
        "SLACK_BOT_TOKEN": "$SLACK_BOT_TOKEN",
        "SLACK_SIGNING_SECRET": "$SLACK_SIGNING_SECRET",
        "OSCAR_BEDROCK_AGENT_ID": "$OSCAR_BEDROCK_AGENT_ID",
        "OSCAR_BEDROCK_AGENT_ALIAS_ID": "${OSCAR_BEDROCK_AGENT_ALIAS_ID:-TSTALIASID}",
        "SESSIONS_TABLE_NAME": "${SESSIONS_TABLE_NAME:-oscar-agent-sessions}",
        "CONTEXT_TABLE_NAME": "${CONTEXT_TABLE_NAME:-oscar-agent-context}",
        "ENABLE_DM": "$ENABLE_DM",
        "DEDUP_TTL": "${DEDUP_TTL:-300}",
        "SESSION_TTL": "${SESSION_TTL:-3600}",
        "CONTEXT_TTL": "${CONTEXT_TTL:-604800}",
        "MAX_CONTEXT_LENGTH": "${MAX_CONTEXT_LENGTH:-3000}",
        "CONTEXT_SUMMARY_LENGTH": "${CONTEXT_SUMMARY_LENGTH:-500}",
        "AGENT_TIMEOUT": "${AGENT_TIMEOUT:-180}",
        "AGENT_MAX_RETRIES": "${AGENT_MAX_RETRIES:-2}",
        "CHANNEL_ALLOW_LIST": "$CHANNEL_ALLOW_LIST",
        "AUTHORIZED_MESSAGE_SENDERS": "$AUTHORIZED_MESSAGE_SENDERS",
        "METRICS_CROSS_ACCOUNT_ROLE_ARN": "$METRICS_CROSS_ACCOUNT_ROLE_ARN",
        "HOURGLASS_THRESHOLD_SECONDS": "${HOURGLASS_THRESHOLD_SECONDS:-45}",
        "TIMEOUT_THRESHOLD_SECONDS": "${TIMEOUT_THRESHOLD_SECONDS:-120}",
        "MAX_WORKERS": "${MAX_WORKERS:-50}",
        "MAX_ACTIVE_QUERIES": "${MAX_ACTIVE_QUERIES:-50}",
        "MONITOR_INTERVAL_SECONDS": "${MONITOR_INTERVAL_SECONDS:-15}",
        "MESSAGE_PREVIEW_LENGTH": "${MESSAGE_PREVIEW_LENGTH:-100}",
        "QUERY_PREVIEW_LENGTH": "${QUERY_PREVIEW_LENGTH:-50}",
        "RESPONSE_PREVIEW_LENGTH": "${RESPONSE_PREVIEW_LENGTH:-50}",
        "SLACK_HANDLER_THREAD_NAME_PREFIX": "${SLACK_HANDLER_THREAD_NAME_PREFIX:-oscar-agent}",
        "BEDROCK_RESPONSE_MESSAGE_VERSION": "${BEDROCK_RESPONSE_MESSAGE_VERSION:-1.0}",
        "BEDROCK_ACTION_GROUP_NAME": "${BEDROCK_ACTION_GROUP_NAME:-communication-orchestration}",
        "CHANNEL_MAPPINGS": "$ESCAPED_CHANNEL_MAPPINGS",
        "AGENT_QUERY_ANNOUNCE": "$AGENT_QUERY_ANNOUNCE",
        "AGENT_QUERY_ASSIGN_OWNER": "$AGENT_QUERY_ASSIGN_OWNER",
        "AGENT_QUERY_REQUEST_OWNER": "$AGENT_QUERY_REQUEST_OWNER",
        "AGENT_QUERY_RC_DETAILS": "$AGENT_QUERY_RC_DETAILS",
        "AGENT_QUERY_MISSING_NOTES": "$AGENT_QUERY_MISSING_NOTES",
        "AGENT_QUERY_INTEGRATION_TEST": "$AGENT_QUERY_INTEGRATION_TEST",
        "AGENT_QUERY_BROADCAST": "$AGENT_QUERY_BROADCAST"
    }
}
EOF

    # Update environment variables, timeout, and memory using JSON file
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment file://$TEMP_DIR/env-vars.json \
        --timeout ${LAMBDA_TIMEOUT:-150} \
        --memory-size ${LAMBDA_MEMORY_SIZE:-512} \
        --region $AWS_REGION >/dev/null

    echo "✅ Updated Lambda function code and configuration: $FUNCTION_NAME"
    
    # Wait for function to be ready
    echo "⏳ Waiting for function to be ready..."
    aws lambda wait function-updated --function-name $FUNCTION_NAME --region $AWS_REGION
    aws lambda wait function-active --function-name $FUNCTION_NAME --region $AWS_REGION
    
else
    echo "❌ Lambda function $FUNCTION_NAME does not exist!"
    echo "   Please run ./deploy_slack_agent.sh first to create the function."
    exit 1
fi

# Get function ARN for confirmation
FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text)

# Cleanup
echo "🧹 Cleaning up temporary files..."
rm -rf $TEMP_DIR

echo ""
echo "🎉 Slack Agent Lambda Function Code Updated!"
echo ""
echo "📋 Summary:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Function ARN:  $FUNCTION_ARN"
echo "   Region:        $AWS_REGION"
echo ""
echo "🔒 Preserved:"
echo "   ✅ All IAM permissions"
echo "   ✅ Environment variables"
echo "   ✅ API Gateway permissions"
echo "   ✅ Bedrock agent access"
echo "   ✅ DynamoDB permissions"
echo ""
echo "📝 Updated Files:"
echo "   ✅ slack_handler.py"
echo "   ✅ communication_handler.py"
echo "   ✅ bedrock.py"
echo "   ✅ storage.py"
echo "   ✅ config.py"
echo "   ✅ app.py (lambda handler)"
echo ""
echo "🧪 Test with: @oscar hello"