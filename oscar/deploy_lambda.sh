#!/bin/bash

# Exit on error
set -e

echo "=== Updating OSCAR Slack Bot Lambda Function ==="

# Check if we should skip environment variable updates (when called from CDK)
SKIP_ENV_UPDATE=${SKIP_ENV_UPDATE:-false}

# Get AWS region from environment or use default
AWS_REGION=${AWS_REGION:-us-west-2}
echo "Using AWS Region: $AWS_REGION"

# Create a temporary directory for the Lambda package
echo "Creating Lambda deployment package..."
mkdir -p lambda_package

# Copy the app.py file and other Python modules
echo "Copying application files..."
cp slack-bot/app.py lambda_package/
cp slack-bot/__init__.py lambda_package/
cp slack-bot/bedrock.py lambda_package/
cp slack-bot/config.py lambda_package/
cp slack-bot/slack_handler.py lambda_package/
cp slack-bot/storage.py lambda_package/

# Verify package structure
if [ ! -f "lambda_package/app.py" ] || [ ! -f "lambda_package/config.py" ]; then
    echo "Error: Application files are missing or incomplete!"
    echo "Please ensure the slack-bot directory contains all required modules."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r slack-bot/requirements.txt -t lambda_package/ --force-reinstall

# Create the zip file
echo "Creating zip file..."
cd lambda_package
zip -r ../lambda_package.zip .
cd ..

# Get Lambda function name from environment or try to get it from CloudFormation stack
if [ -z "$LAMBDA_FUNCTION_NAME" ]; then
    echo "Getting Lambda function name from CloudFormation stack..."
    LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks \
        --stack-name OscarSlackBotStack \
        --query "Stacks[0].Outputs[?OutputKey=='LambdaStackLambdaFunctionName'].OutputValue" \
        --output text \
        --region $AWS_REGION 2>/dev/null || echo "")
    
    # If empty, try the main stack output
    if [ -z "$LAMBDA_FUNCTION_NAME" ]; then
        LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks \
            --stack-name OscarSlackBotStack \
            --query "Stacks[0].Outputs[?OutputKey=='SlackBotFunctionName'].OutputValue" \
            --output text \
            --region $AWS_REGION 2>/dev/null || echo "")
    fi
    
    # If still empty, use the configured name from context or default
    if [ -z "$LAMBDA_FUNCTION_NAME" ]; then
        echo "Warning: Could not get function name from CloudFormation, using default name"
        LAMBDA_FUNCTION_NAME="oscar-slack-bot"
    fi
fi

echo "Updating Lambda function: $LAMBDA_FUNCTION_NAME"

# Update the Lambda function
echo "Updating Lambda function code..."
aws lambda update-function-code \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --zip-file fileb://lambda_package.zip \
  --region $AWS_REGION

# Verify Lambda update was successful
if [ $? -eq 0 ]; then
    echo "Lambda function code updated successfully!"
else
    echo "Error: Failed to update Lambda function code!"
    exit 1
fi

# Update Lambda environment variables (skip if called from CDK)
if [ "$SKIP_ENV_UPDATE" = "true" ]; then
    echo "Skipping environment variable update (managed by CDK)"
else
    echo "Updating Lambda environment variables..."

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    # Load each line individually to handle multi-line values
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        if [[ ! "$line" =~ ^[[:space:]]*# && -n "$line" ]]; then
            # Extract variable name and value
            var_name=$(echo "$line" | cut -d= -f1)
            var_value=$(echo "$line" | cut -d= -f2-)
            
            # Export the variable
            export "$var_name"="$var_value"
            echo "Exported $var_name"
        fi
    done < ".env"
elif [ -f "slack-bot/.env" ]; then
    echo "Loading environment variables from slack-bot/.env file..."
    # Load each line individually to handle multi-line values
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        if [[ ! "$line" =~ ^[[:space:]]*# && -n "$line" ]]; then
            # Extract variable name and value
            var_name=$(echo "$line" | cut -d= -f1)
            var_value=$(echo "$line" | cut -d= -f2-)
            
            # Export the variable
            export "$var_name"="$var_value"
            echo "Exported $var_name"
        fi
    done < "slack-bot/.env"
fi

# Get table names from CloudFormation outputs if not provided
if [ -z "$SESSIONS_TABLE_NAME" ]; then
    echo "Getting sessions table name from CloudFormation stack..."
    SESSIONS_TABLE_NAME=$(aws cloudformation describe-stacks \
        --stack-name OscarSlackBotStack \
        --query "Stacks[0].Outputs[?OutputKey=='StorageStackSessionsTableName'].OutputValue" \
        --output text \
        --region $AWS_REGION 2>/dev/null || echo "oscar-sessions-v2")
fi

if [ -z "$CONTEXT_TABLE_NAME" ]; then
    echo "Getting context table name from CloudFormation stack..."
    CONTEXT_TABLE_NAME=$(aws cloudformation describe-stacks \
        --stack-name OscarSlackBotStack \
        --query "Stacks[0].Outputs[?OutputKey=='StorageStackContextTableName'].OutputValue" \
        --output text \
        --region $AWS_REGION 2>/dev/null || echo "oscar-context")
fi

echo "Using sessions table: $SESSIONS_TABLE_NAME"
echo "Using context table: $CONTEXT_TABLE_NAME"

# Create a temporary file for the environment variables
echo "{" > env_vars.json
echo "  \"KNOWLEDGE_BASE_ID\": \"${KNOWLEDGE_BASE_ID}\"," >> env_vars.json
# Set default MODEL_ARN if not provided
DEFAULT_MODEL_ARN="arn:aws:bedrock:${AWS_REGION}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
MODEL_ARN=${MODEL_ARN:-$DEFAULT_MODEL_ARN}
echo "Using Model ARN: ${MODEL_ARN}"
echo "  \"MODEL_ARN\": \"${MODEL_ARN}\"," >> env_vars.json
echo "  \"SLACK_BOT_TOKEN\": \"${SLACK_BOT_TOKEN}\"," >> env_vars.json
echo "  \"SLACK_SIGNING_SECRET\": \"${SLACK_SIGNING_SECRET}\"," >> env_vars.json
echo "  \"SESSIONS_TABLE_NAME\": \"${SESSIONS_TABLE_NAME}\"," >> env_vars.json
echo "  \"CONTEXT_TABLE_NAME\": \"${CONTEXT_TABLE_NAME}\"," >> env_vars.json
# Note: These configuration values are now managed by CDK from cdk.context.json
# We only set them here if they're explicitly provided as environment variables
# Otherwise, CDK will have already set them from context during initial deployment
if [ -n "$DEDUP_TTL" ]; then
    echo "  \"DEDUP_TTL\": \"${DEDUP_TTL}\"," >> env_vars.json
fi
if [ -n "$SESSION_TTL" ]; then
    echo "  \"SESSION_TTL\": \"${SESSION_TTL}\"," >> env_vars.json
fi
if [ -n "$CONTEXT_TTL" ]; then
    echo "  \"CONTEXT_TTL\": \"${CONTEXT_TTL}\"," >> env_vars.json
fi
if [ -n "$MAX_CONTEXT_LENGTH" ]; then
    echo "  \"MAX_CONTEXT_LENGTH\": \"${MAX_CONTEXT_LENGTH}\"," >> env_vars.json
fi
if [ -n "$CONTEXT_SUMMARY_LENGTH" ]; then
    echo "  \"CONTEXT_SUMMARY_LENGTH\": \"${CONTEXT_SUMMARY_LENGTH}\"," >> env_vars.json
fi

# Add ENABLE_DM as the last item (with or without comma)
if [ ! -z "$PROMPT_TEMPLATE" ]; then
    # If PROMPT_TEMPLATE exists, add ENABLE_DM with a comma
    echo "  \"ENABLE_DM\": \"${ENABLE_DM:-false}\"," >> env_vars.json
    
    # Create a temporary Python script to properly escape the PROMPT_TEMPLATE
    cat > escape_prompt.py << EOF
import json
import sys

with open('prompt_template.txt', 'r') as f:
    prompt = f.read()

escaped_prompt = json.dumps(prompt)[1:-1]  # Remove surrounding quotes
print(escaped_prompt)
EOF
    
    # Write the PROMPT_TEMPLATE to a file
    echo "$PROMPT_TEMPLATE" > prompt_template.txt
    
    # Use Python to properly escape the PROMPT_TEMPLATE
    ESCAPED_PROMPT=$(python escape_prompt.py)
    
    # Add the PROMPT_TEMPLATE to the JSON (as the last item, no comma)
    echo "  \"PROMPT_TEMPLATE\": \"${ESCAPED_PROMPT}\"" >> env_vars.json
    
    # Clean up
    rm prompt_template.txt escape_prompt.py
else
    # If no PROMPT_TEMPLATE, add ENABLE_DM without a comma (as the last item)
    echo "  \"ENABLE_DM\": \"${ENABLE_DM:-false}\"" >> env_vars.json
fi

# Close the JSON object
echo "}" >> env_vars.json

# Create a temporary file with the environment variables JSON
echo "{\"Variables\": $(cat env_vars.json)}" > lambda_env.json

# Update Lambda configuration with new environment variables
aws lambda update-function-configuration \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --region $AWS_REGION \
    --environment file://lambda_env.json

# Clean up environment variable files
rm env_vars.json lambda_env.json
fi

# Clean up deployment files
echo "Cleaning up..."
rm -rf lambda_package
rm lambda_package.zip

echo "Lambda deployment completed successfully!"