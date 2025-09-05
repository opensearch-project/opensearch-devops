#!/bin/bash

# Jenkins Lambda Update Script
# Updates only the Lambda function code without resetting permissions or configuration

set -e

echo "🔄 Starting Jenkins Lambda code update..."

# Configuration
AWS_REGION="us-east-1"
FUNCTION_NAME="oscar-jenkins-agent"

echo "📋 Configuration:"
echo "  AWS Region: $AWS_REGION"
echo "  Function Name: $FUNCTION_NAME"

# Navigate to jenkins directory
cd "$(dirname "$0")/.."

# Verify function exists
echo "🔍 Verifying Lambda function exists..."
if ! aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "❌ Error: Lambda function '$FUNCTION_NAME' does not exist"
    echo "💡 Run the full deployment script first: ./deployment/deploy.sh"
    exit 1
fi

echo "✅ Lambda function exists"

# Create deployment package
echo "📦 Creating deployment package..."
TEMP_DIR=$(mktemp -d)
echo "📁 Using temporary directory: $TEMP_DIR"

# Copy all Python files
cp *.py "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -t "$TEMP_DIR/" --quiet

# Create ZIP package
echo "🗜️  Creating ZIP package..."
cd "$TEMP_DIR"
zip -r ../jenkins-lambda-update.zip . > /dev/null
cd - > /dev/null

# Move the ZIP to deployment directory
mv "$TEMP_DIR/../jenkins-lambda-update.zip" deployment/jenkins-lambda-update.zip

# Clean up temporary directory
rm -rf "$TEMP_DIR"

# Update Lambda function code
echo "🚀 Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://deployment/jenkins-lambda-update.zip \
    --region "$AWS_REGION" > /dev/null

echo "✅ Lambda function code updated successfully"

# Optionally update configuration (uncomment if needed)
# echo "⚙️  Updating Lambda configuration..."
# aws lambda update-function-configuration \
#     --function-name "$FUNCTION_NAME" \
#     --timeout 180 \
#     --memory-size 512 \
#     --environment Variables="{JENKINS_URL=https://build.ci.opensearch.org,LOG_LEVEL=INFO}" \
#     --region "$AWS_REGION" > /dev/null

# Clean up deployment package
rm deployment/jenkins-lambda-update.zip

# Get updated function info
echo "📋 Updated function details:"
aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" --query '{
    FunctionName: Configuration.FunctionName,
    Runtime: Configuration.Runtime,
    Handler: Configuration.Handler,
    CodeSize: Configuration.CodeSize,
    LastModified: Configuration.LastModified,
    Version: Configuration.Version
}' --output table

echo ""
echo "🎉 Jenkins Lambda code update completed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Test the updated function: python deployment/test_deployment.py"
echo "2. Monitor CloudWatch logs for any issues"
echo ""
echo "💡 To update configuration as well, uncomment the configuration update section in this script"