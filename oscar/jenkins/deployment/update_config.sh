#!/bin/bash

# Jenkins Lambda Configuration Update Script
# Updates Lambda function configuration (environment variables, timeout, memory, etc.)

set -e

echo "⚙️  Starting Jenkins Lambda configuration update..."

# Configuration
AWS_REGION="us-east-1"
FUNCTION_NAME="oscar-jenkins-agent"

echo "📋 Configuration:"
echo "  AWS Region: $AWS_REGION"
echo "  Function Name: $FUNCTION_NAME"

# Verify function exists
echo "🔍 Verifying Lambda function exists..."
if ! aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "❌ Error: Lambda function '$FUNCTION_NAME' does not exist"
    echo "💡 Run the full deployment script first: ./deployment/deploy.sh"
    exit 1
fi

echo "✅ Lambda function exists"

# Update Lambda configuration
echo "⚙️  Updating Lambda function configuration..."
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --timeout 180 \
    --memory-size 512 \
    --environment Variables="{JENKINS_URL=https://build.ci.opensearch.org,LOG_LEVEL=INFO}" \
    --region "$AWS_REGION" > /dev/null

echo "✅ Lambda function configuration updated successfully"

# Get updated function info
echo "📋 Updated function configuration:"
aws lambda get-function-configuration --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query '{
    FunctionName: FunctionName,
    Runtime: Runtime,
    Handler: Handler,
    MemorySize: MemorySize,
    Timeout: Timeout,
    Environment: Environment,
    LastModified: LastModified
}' --output table

echo ""
echo "🎉 Jenkins Lambda configuration update completed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Test the updated configuration: python deployment/test_deployment.py"
echo "2. Monitor CloudWatch logs for any issues"