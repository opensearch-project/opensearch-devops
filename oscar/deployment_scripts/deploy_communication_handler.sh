#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Deploy OSCAR Communication Handler Lambda Function
# FULL DEPLOYMENT - Creates function, role, and permissions with proper dependencies

set -e

echo "🚀 Deploying OSCAR Communication Handler Lambda Function..."

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
required_vars=("SLACK_BOT_TOKEN" "AWS_REGION")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

# Set default values
AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="oscar-communication-handler"
LAMBDA_ROLE_NAME="oscar-communication-handler-role"

# Verify region configuration
echo "🌍 Using AWS Region: $AWS_REGION"

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
zip -r ../communication-handler.zip . -x "*.pyc" "*/__pycache__/*"
cd - > /dev/null

DEPLOYMENT_PACKAGE="$TEMP_DIR/../communication-handler.zip"
echo "✅ Created deployment package: $DEPLOYMENT_PACKAGE"

# Check if IAM role exists, create if not
echo "🔐 Checking IAM role..."
if ! aws iam get-role --role-name $LAMBDA_ROLE_NAME --region $AWS_REGION > /dev/null 2>&1; then
    echo "Creating IAM role: $LAMBDA_ROLE_NAME"
    
    # Create trust policy
    cat > $TEMP_DIR/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create the role
    aws iam create-role \
        --role-name $LAMBDA_ROLE_NAME \
        --assume-role-policy-document file://$TEMP_DIR/trust-policy.json \
        --region $AWS_REGION

    # Attach basic Lambda execution policy
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
        --region $AWS_REGION

    # Create and attach custom policy for Bedrock and DynamoDB access
    cat > $TEMP_DIR/lambda-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:InvokeModel",
        "bedrock:GetAgent",
        "bedrock:GetKnowledgeBase"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/oscar-agent-context",
        "arn:aws:dynamodb:*:*:table/oscar-agent-sessions"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-name "CommunicationHandlerPolicy" \
        --policy-document file://$TEMP_DIR/lambda-policy.json \
        --region $AWS_REGION

    echo "✅ Created IAM role: $LAMBDA_ROLE_NAME"
    
    # Wait for role to be available
    echo "⏳ Waiting for IAM role to be available..."
    sleep 10
else
    echo "✅ IAM role already exists: $LAMBDA_ROLE_NAME"
    
    # Update the policy to ensure it has the correct permissions
    echo "🔄 Updating IAM role policy..."
    cat > $TEMP_DIR/lambda-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:InvokeModel",
        "bedrock:GetAgent",
        "bedrock:GetKnowledgeBase"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/oscar-agent-context",
        "arn:aws:dynamodb:*:*:table/oscar-agent-sessions"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-name "CommunicationHandlerPolicy" \
        --policy-document file://$TEMP_DIR/lambda-policy.json \
        --region $AWS_REGION

    echo "✅ Updated IAM role policy"
fi

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --region $AWS_REGION --query 'Role.Arn' --output text)
echo "📋 Using IAM role: $ROLE_ARN"

# Check if Lambda function exists
echo "🔍 Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION > /dev/null 2>&1; then
    echo "📝 Updating existing Lambda function..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://$DEPLOYMENT_PACKAGE \
        --region $AWS_REGION

    # Update function configuration
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --runtime python3.12 \
        --handler lambda_function.lambda_handler \
        --timeout ${LAMBDA_TIMEOUT:-150} \
        --memory-size ${LAMBDA_MEMORY_SIZE:-512} \
        --environment Variables="{SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN,CONTEXT_TABLE_NAME=oscar-agent-context}" \
        --region $AWS_REGION

    echo "✅ Updated Lambda function: $FUNCTION_NAME"
else
    echo "🆕 Creating new Lambda function..."
    
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.12 \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://$DEPLOYMENT_PACKAGE \
        --timeout ${LAMBDA_TIMEOUT:-150} \
        --memory-size ${LAMBDA_MEMORY_SIZE:-512} \
        --environment Variables="{SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN,CONTEXT_TABLE_NAME=oscar-agent-context}" \
        --region $AWS_REGION

    echo "✅ Created Lambda function: $FUNCTION_NAME"
fi

# Get function ARN
FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text)
echo "📋 Lambda function ARN: $FUNCTION_ARN"

# Add permission for Bedrock to invoke the Lambda function
echo "🔐 Adding Bedrock invoke permission..."
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id "bedrock-invoke-permission" \
    --action lambda:InvokeFunction \
    --principal bedrock.amazonaws.com \
    --region $AWS_REGION \
    2>/dev/null || echo "⚠️  Permission may already exist"

# Cleanup
echo "🧹 Cleaning up temporary files..."
rm -rf $TEMP_DIR

echo ""
echo "🎉 Communication Handler Lambda Function Deployment Complete!"
echo ""
echo "📋 Summary:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Function ARN:  $FUNCTION_ARN"
echo "   IAM Role:      $ROLE_ARN"
echo "   Region:        $AWS_REGION"
echo ""
echo "✅ Configured with proper permissions for:"
echo "   📊 DynamoDB access (oscar-agent-context, oscar-agent-sessions)"
echo "   🤖 Bedrock agent invocation"
echo "   📝 CloudWatch logging"
echo ""
echo "🧪 Test command:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"actionGroup\": \"communication-orchestration\", \"apiPath\": \"/send_automated_message\"}' --cli-binary-format raw-in-base64-out --region $AWS_REGION test.json && cat test.json"