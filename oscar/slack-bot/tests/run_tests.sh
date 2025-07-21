#!/bin/bash

# Run all tests
cd "$(dirname "$0")/.."

# Check for required dependencies
echo "Checking for required dependencies..."

# Function to check if a Python package is installed
check_dependency() {
    python -c "import $1" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "Error: Required dependency '$1' is missing. Please install it using: pip install $1"
        exit 1
    else
        echo "✓ $1 is installed"
    fi
}

# Check each required dependency
check_dependency pytest
check_dependency slack_bolt
check_dependency boto3

# Set required environment variables for testing if not already set
if [ -z "$SLACK_BOT_TOKEN" ]; then
    export SLACK_BOT_TOKEN="test-bot-token"
    echo "Set SLACK_BOT_TOKEN for testing"
fi

if [ -z "$SLACK_SIGNING_SECRET" ]; then
    export SLACK_SIGNING_SECRET="test-signing-secret"
    echo "Set SLACK_SIGNING_SECRET for testing"
fi

if [ -z "$KNOWLEDGE_BASE_ID" ]; then
    export KNOWLEDGE_BASE_ID="test-kb-id"
    echo "Set KNOWLEDGE_BASE_ID for testing"
fi

if [ -z "$MODEL_ARN" ]; then
    export MODEL_ARN="arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
    echo "Set MODEL_ARN for testing"
fi

# Run tests
echo "Running tests..."
PYTHONPATH=. pytest tests/ -v