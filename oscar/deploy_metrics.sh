#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Deploy the new minimal metrics implementation
# FULL DEPLOYMENT - Creates functions, roles, and permissions

set -e

echo "🚀 Deploying new minimal metrics implementation"

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

# Verify region configuration
echo "🌍 Using AWS Region: $AWS_REGION"
if [ "$AWS_REGION" != "us-east-1" ]; then
    echo "⚠️  Warning: Expected region us-east-1, but using $AWS_REGION"
fi

# Use the correct VPC role ARN
ROLE_ARN="${LAMBDA_EXECUTION_ROLE_ARN:-arn:aws:iam::395380602281:role/oscar-metrics-lambda-vpc-role}"
echo "Using IAM role: $ROLE_ARN"

# Create deployment package
echo "📦 Creating deployment package..."
rm -rf new-package new-package.zip
mkdir new-package

# Create comprehensive requirements.txt for metrics
cat > new-package/requirements.txt << EOF
# Core AWS dependencies
boto3>=1.34.0
botocore>=1.34.0

# HTTP and networking
requests>=2.31.0
urllib3>=2.0.0

# Additional dependencies for metrics functionality
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
if ! pip install -r new-package/requirements.txt -t new-package/ --upgrade --quiet; then
    echo "❌ Failed to install dependencies with pip. Trying alternative approach..."
    # Try installing each dependency individually
    while IFS= read -r line; do
        if [[ $line =~ ^[a-zA-Z] ]]; then
            echo "  Installing: $line"
            pip install "$line" -t new-package/ --upgrade --quiet || {
                echo "❌ Failed to install $line"
                exit 1
            }
        fi
    done < new-package/requirements.txt
fi

# Verify critical dependencies
echo "🔍 Verifying dependencies..."
CRITICAL_DEPS=("boto3" "botocore" "requests")
for dep in "${CRITICAL_DEPS[@]}"; do
    if [ ! -d "new-package/$dep" ] && [ ! -d "new-package/${dep//_/-}" ]; then
        echo "❌ Missing dependency: $dep"
        pip install "$dep" -t new-package/ --upgrade --quiet || {
            echo "❌ Failed to install $dep"
            exit 1
        }
    fi
done

echo "✅ Dependencies verified"

# Copy source code
cp metrics/*.py new-package/

# Remove requirements.txt from package (not needed in Lambda)
rm -f new-package/requirements.txt

# Create zip
cd new-package && zip -r ../new-package.zip . -q && cd ..
rm -rf new-package

# Create environment variables - match .env file exactly
cat > env-vars.json << EOF
{
    "Variables": {
        "OPENSEARCH_HOST": "$OPENSEARCH_HOST",
        "OPENSEARCH_REGION": "$OPENSEARCH_REGION",
        "OPENSEARCH_SERVICE": "$OPENSEARCH_SERVICE",
        "OPENSEARCH_DOMAIN_ARN": "$OPENSEARCH_DOMAIN_ARN",
        "VPC_ID": "$VPC_ID",
        "SUBNET_IDS": "$SUBNET_IDS",
        "SECURITY_GROUP_ID": "$SECURITY_GROUP_ID",
        "LOG_LEVEL": "${LOG_LEVEL:-INFO}",
        "REQUEST_TIMEOUT": "${REQUEST_TIMEOUT:-30}",
        "MAX_RESULTS": "${MAX_RESULTS:-50}",
        "MOCK_MODE": "${MOCK_MODE:-false}",
        "AGENT_TYPE": "build-metrics",
        "METRICS_ROLE_ARN": "${METRICS_ROLE_ARN:-arn:aws:iam::979020455945:role/OpenSearchOscarAccessRole}"
    }
}
EOF

# Create VPC configuration
IFS=',' read -ra SUBNET_ARRAY <<< "$SUBNET_IDS"
subnet_json=""
for i in "${!SUBNET_ARRAY[@]}"; do
    if [ $i -eq 0 ]; then
        subnet_json="\"${SUBNET_ARRAY[$i]}\""
    else
        subnet_json="$subnet_json, \"${SUBNET_ARRAY[$i]}\""
    fi
done

cat > vpc-config.json << EOF
{
    "SubnetIds": [$subnet_json],
    "SecurityGroupIds": ["$SECURITY_GROUP_ID"]
}
EOF

# Deploy all agent functions
AGENT_FUNCTIONS=(
    "oscar-test-metrics-agent-new:test-metrics"
    "oscar-build-metrics-agent-new:build-metrics"
    "oscar-release-metrics-agent-new:release-metrics"
    "oscar-deployment-metrics-agent-new:deployment-metrics"
)

for func_config in "${AGENT_FUNCTIONS[@]}"; do
    IFS=':' read -ra FUNC_PARTS <<< "$func_config"
    FUNCTION_NAME="${FUNC_PARTS[0]}"
    AGENT_TYPE="${FUNC_PARTS[1]}"
    
    echo "🚀 Deploying $FUNCTION_NAME ($AGENT_TYPE)..."
    
    # Update environment variables for this agent type
    cat > env-vars.json << EOF
{
    "Variables": {
        "OPENSEARCH_HOST": "$OPENSEARCH_HOST",
        "OPENSEARCH_REGION": "$OPENSEARCH_REGION",
        "OPENSEARCH_SERVICE": "$OPENSEARCH_SERVICE",
        "OPENSEARCH_DOMAIN_ARN": "$OPENSEARCH_DOMAIN_ARN",
        "VPC_ID": "$VPC_ID",
        "SUBNET_IDS": "$SUBNET_IDS",
        "SECURITY_GROUP_ID": "$SECURITY_GROUP_ID",
        "LOG_LEVEL": "${LOG_LEVEL:-INFO}",
        "REQUEST_TIMEOUT": "${REQUEST_TIMEOUT:-30}",
        "MAX_RESULTS": "${MAX_RESULTS:-50}",
        "MOCK_MODE": "${MOCK_MODE:-false}",
        "AGENT_TYPE": "$AGENT_TYPE",
        "METRICS_ROLE_ARN": "${METRICS_ROLE_ARN:-arn:aws:iam::979020455945:role/OpenSearchOscarAccessRole}"
    }
}
EOF
    
    # Delete if exists
    aws lambda delete-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" 2>/dev/null || true
    
    # Wait for deletion
    sleep 2
    
    # Create new function
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime python3.12 \
        --role "$ROLE_ARN" \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://new-package.zip \
        --timeout 60 \
        --memory-size 256 \
        --vpc-config file://vpc-config.json \
        --environment file://env-vars.json \
        --region "$AWS_REGION" >/dev/null
    
    echo "✅ $FUNCTION_NAME deployed"
    
    # Wait for function to be ready
    aws lambda wait function-active --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
done

echo "⏳ Waiting for functions to be ready..."
for func_config in "${AGENT_FUNCTIONS[@]}"; do
    IFS=':' read -ra FUNC_PARTS <<< "$func_config"
    FUNCTION_NAME="${FUNC_PARTS[0]}"
    aws lambda wait function-active --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
done
echo "✅ All functions ready for testing"

echo "✅ All functions deployed successfully"

# Add Bedrock agent permissions
echo ""
echo "🔐 Adding Bedrock agent permissions..."

# Actual agent IDs from your deployment
AGENT_PERMISSIONS=(
    "YXSZJ659S7:oscar-test-metrics-agent-new:TestAnalyzer"
    "0NBATJIVCH:oscar-build-metrics-agent-new:BuildAnalyzer"
    "4FCARBPEYB:oscar-release-metrics-agent-new:ReleaseAnalyzer"
    "BIHPD6OLO0:oscar-deployment-metrics-agent-new:DeploymentAnalyzer"
)

# Function to add permission
add_permission() {
    local agent_id=$1
    local function_name=$2
    local agent_name=$3
    
    echo "  Adding permission for $agent_name..."
    
    aws lambda add-permission \
        --function-name "$function_name" \
        --statement-id "bedrock-v2-$agent_id-$(date +%s)" \
        --action "lambda:InvokeFunction" \
        --principal "bedrock.amazonaws.com" \
        --source-arn "arn:aws:bedrock:$AWS_REGION:395380602281:agent/$agent_id" \
        --region "$AWS_REGION" >/dev/null 2>&1 || echo "    (Permission may already exist)"
    
    echo "    ✅ Permission added"
}

# Add permissions for each agent
for entry in "${AGENT_PERMISSIONS[@]}"; do
    IFS=':' read -ra PARTS <<< "$entry"
    agent_id="${PARTS[0]}"
    function_name="${PARTS[1]}"
    agent_name="${PARTS[2]}"
    
    add_permission "$agent_id" "$function_name" "$agent_name"
done

echo "✅ Bedrock permissions configured"

# Cleanup
rm -f new-package.zip env-vars.json vpc-config.json

echo ""
echo "🧪 Test commands:"
echo "# Basic test:"
echo "aws lambda invoke --function-name oscar-build-metrics-agent-new --payload '{\"function\": \"test_basic\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json | jq ."
echo "# Role assumption test:"
echo "aws lambda invoke --function-name oscar-build-metrics-agent-new --payload '{\"function\": \"test_role_only\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json | jq ."
echo "# Metrics tests:"
echo "aws lambda invoke --function-name oscar-build-metrics-agent-new --payload '{\"function\": \"get_build_metrics\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json | jq ."
echo "aws lambda invoke --function-name oscar-test-metrics-agent-new --payload '{\"function\": \"get_test_metrics\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json | jq ."