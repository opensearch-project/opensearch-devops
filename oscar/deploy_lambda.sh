#!/bin/bash

# Exit on error
set -e

echo "=== Updating OSCAR Slack Bot Lambda Function ==="

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

# Get Lambda function name from environment or use default
LAMBDA_FUNCTION_NAME=${LAMBDA_FUNCTION_NAME:-oscar-slack-bot}
echo "Updating Lambda function: $LAMBDA_FUNCTION_NAME"

# Update the Lambda function
echo "Updating Lambda function code..."
aws lambda update-function-code \
  --function-name $LAMBDA_FUNCTION_NAME \
  --zip-file fileb://lambda_package.zip \
  --region $AWS_REGION

# Verify Lambda update was successful
if [ $? -eq 0 ]; then
    echo "Lambda function code updated successfully!"
else
    echo "Error: Failed to update Lambda function code!"
    exit 1
fi

# Update Lambda environment variables
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
echo "  \"SESSIONS_TABLE_NAME\": \"${SESSIONS_TABLE_NAME:-oscar-sessions-v2}\"," >> env_vars.json
echo "  \"CONTEXT_TABLE_NAME\": \"${CONTEXT_TABLE_NAME:-oscar-context}\"," >> env_vars.json
echo "  \"DEDUP_TTL\": \"${DEDUP_TTL:-300}\"," >> env_vars.json
echo "  \"SESSION_TTL\": \"${SESSION_TTL:-3600}\"," >> env_vars.json
echo "  \"CONTEXT_TTL\": \"${CONTEXT_TTL:-604800}\"," >> env_vars.json
echo "  \"MAX_CONTEXT_LENGTH\": \"${MAX_CONTEXT_LENGTH:-3000}\"," >> env_vars.json
echo "  \"CONTEXT_SUMMARY_LENGTH\": \"${CONTEXT_SUMMARY_LENGTH:-500}\"," >> env_vars.json

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
    --function-name $LAMBDA_FUNCTION_NAME \
    --region $AWS_REGION \
    --environment file://lambda_env.json

# Clean up
echo "Cleaning up..."
rm -rf lambda_package
rm lambda_package.zip
rm env_vars.json lambda_env.json

echo "Lambda deployment completed successfully!"