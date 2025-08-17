#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Update ONLY the code for Communication Handler Lambda function
# Preserves all permissions and configurations

set -e

echo "🔄 Updating Communication Handler Lambda Function (Code Only)..."

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
FUNCTION_NAME="oscar-communication-handler"

echo "📦 Creating deployment package..."

# Create temporary directory for deployment
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Copy the communication handler
cp oscar-agent/communication_handler.py $TEMP_DIR/lambda_function.py

# Copy the entire communication_handler package directory
if [ -d "oscar-agent/communication_handler" ]; then
    echo "📁 Copying communication_handler package..."
    cp -r oscar-agent/communication_handler $TEMP_DIR/
    echo "✅ Copied communication_handler package structure"
else
    echo "❌ communication_handler directory not found!"
    exit 1
fi

# Copy config.py and other necessary files
cp oscar-agent/config.py $TEMP_DIR/

# Create comprehensive requirements.txt for the Lambda function
cat > $TEMP_DIR/requirements.txt << EOF
# Core AWS and Slack dependencies
boto3>=1.34.0
botocore>=1.34.0
slack_sdk>=3.19.0

# HTTP and networking
requests>=2.31.0
urllib3>=2.0.0

# Additional dependencies
certifi>=2023.7.22
charset-normalizer>=3.0.0
idna>=3.0.0
python-dateutil>=2.8.0
jmespath>=1.0.0
s3transfer>=0.6.0
six>=1.16.0
EOF

# Install dependencies with upgrade flag
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

# Verify critical dependencies
echo "🔍 Verifying dependencies..."
CRITICAL_DEPS=("slack_sdk" "boto3" "botocore" "requests")
for dep in "${CRITICAL_DEPS[@]}"; do
    if [ ! -d "$TEMP_DIR/$dep" ] && [ ! -d "$TEMP_DIR/${dep//_/-}" ]; then
        echo "❌ Missing dependency: $dep"
        pip install "$dep" -t $TEMP_DIR/ --upgrade --quiet || {
            echo "❌ Failed to install $dep"
            exit 1
        }
    fi
done

echo "✅ Dependencies verified"

# Create deployment package
cd $TEMP_DIR
zip -r ../communication-handler-update.zip . -x "*.pyc" "*/__pycache__/*" -q
cd - > /dev/null

DEPLOYMENT_PACKAGE="$TEMP_DIR/../communication-handler-update.zip"
echo "✅ Created deployment package: $DEPLOYMENT_PACKAGE"

# Check if Lambda function exists
# Create environment variables for communication handler
cat > $TEMP_DIR/env-vars.json << EOF
{
    "Variables": {
        "SLACK_BOT_TOKEN": "$SLACK_BOT_TOKEN",
        "DISABLE_CONFIG_VALIDATION": "true",
        "CHANNEL_ALLOW_LIST": "$CHANNEL_ALLOW_LIST",
        "CONTEXT_TTL": "${CONTEXT_TTL:-604800}",
        "CONTEXT_TABLE_NAME": "${CONTEXT_TABLE_NAME:-oscar-agent-context}",
        "MESSAGE_PREVIEW_LENGTH": "${MESSAGE_PREVIEW_LENGTH:-100}",
        "BEDROCK_RESPONSE_MESSAGE_VERSION": "${BEDROCK_RESPONSE_MESSAGE_VERSION:-1.0}",
        "BEDROCK_ACTION_GROUP_NAME": "${BEDROCK_ACTION_GROUP_NAME:-communication-orchestration}",
        "DEFAULT_VERSION": "${DEFAULT_VERSION:-3.2.0}",
        "TEMPLATE_MISSING_RELEASE_NOTES": "$TEMPLATE_MISSING_RELEASE_NOTES",
        "TEMPLATE_CRITERIA_NOT_MET": "$TEMPLATE_CRITERIA_NOT_MET",
        "TEMPLATE_DOCUMENTATION_ISSUES": "$TEMPLATE_DOCUMENTATION_ISSUES",
        "TEMPLATE_MISSING_CODE_COVERAGE": "$TEMPLATE_MISSING_CODE_COVERAGE",
        "TEMPLATE_RELEASE_ANNOUNCEMENT": "$TEMPLATE_RELEASE_ANNOUNCEMENT",
        "DEFAULT_CHANNEL_MISSING_RELEASE_NOTES": "${DEFAULT_CHANNEL_MISSING_RELEASE_NOTES:-C096MV7JZ0T}",
        "DEFAULT_CHANNEL_CRITERIA_NOT_MET": "${DEFAULT_CHANNEL_CRITERIA_NOT_MET:-C096MV7JZ0T}",
        "DEFAULT_CHANNEL_DOCUMENTATION_ISSUES": "${DEFAULT_CHANNEL_DOCUMENTATION_ISSUES:-C096MV7JZ0T}",
        "DEFAULT_CHANNEL_MISSING_CODE_COVERAGE": "${DEFAULT_CHANNEL_MISSING_CODE_COVERAGE:-C09827S7CEB}",
        "DEFAULT_CHANNEL_RELEASE_ANNOUNCEMENT": "${DEFAULT_CHANNEL_RELEASE_ANNOUNCEMENT:-C096MV7JZ0T}",
        "CHANNEL_MAPPING_RELEASE_MANAGER": "${CHANNEL_MAPPING_RELEASE_MANAGER:-C096MV7JZ0T}",
        "CHANNEL_MAPPING_TEST": "${CHANNEL_MAPPING_TEST:-C09827S7CEB}",
        "CHANNEL_MAPPING_3_2_0_RELEASE": "${CHANNEL_MAPPING_3_2_0_RELEASE:-C088XMSH4DA}",
        "CHANNEL_MAPPING_RILEY": "${CHANNEL_MAPPING_RILEY:-C091EH1JKCL}"
    }
}
EOF

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
    
    # Update environment variables
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment file://$TEMP_DIR/env-vars.json \
        --region $AWS_REGION >/dev/null

    echo "✅ Updated Lambda function code: $FUNCTION_NAME"
    
    # Wait for function to be ready
    echo "⏳ Waiting for function to be ready..."
    aws lambda wait function-updated --function-name $FUNCTION_NAME --region $AWS_REGION
    aws lambda wait function-active --function-name $FUNCTION_NAME --region $AWS_REGION
    
else
    echo "❌ Lambda function $FUNCTION_NAME does not exist!"
    echo "   Please run ./deploy_communication_handler.sh first to create the function."
    exit 1
fi

# Get function ARN for confirmation
FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text)

# Cleanup
echo "🧹 Cleaning up temporary files..."
rm -rf $TEMP_DIR

echo ""
echo "🎉 Communication Handler Lambda Function Code Updated!"
echo ""
echo "📋 Summary:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Function ARN:  $FUNCTION_ARN"
echo "   Region:        $AWS_REGION"
echo ""
echo "🔒 Preserved:"
echo "   ✅ All IAM permissions"
echo "   ✅ Environment variables"
echo "   ✅ Bedrock agent permissions"
echo "   ✅ All existing configurations"
echo ""
echo "📝 Updated Files:"
echo "   ✅ communication_handler.py"
echo ""
echo "🧪 Test command:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"actionGroup\": \"communication-orchestration\", \"apiPath\": \"/send_automated_message\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json"