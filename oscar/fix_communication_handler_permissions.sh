#!/bin/bash
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

# Fix DynamoDB permissions for oscar-communication-handler

set -e

echo "🔧 Fixing DynamoDB Permissions for Communication Handler..."

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

# Set default values
AWS_REGION=${AWS_REGION:-us-east-1}
ROLE_NAME="oscar-communication-handler-role"
POLICY_NAME="CommunicationHandlerPolicy"

echo "🌍 Using AWS Region: $AWS_REGION"
echo "🔐 Role Name: $ROLE_NAME"
echo "📋 Policy Name: $POLICY_NAME"

# Create updated policy document with DynamoDB permissions
cat > /tmp/communication-handler-policy.json << EOF
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
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:${AWS_REGION}:*:table/oscar-agent-context",
                "arn:aws:dynamodb:${AWS_REGION}:*:table/oscar-agent-sessions"
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

echo "📝 Created updated policy document with DynamoDB permissions"

# Update the role policy
echo "🔄 Updating IAM role policy..."
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name $POLICY_NAME \
    --policy-document file:///tmp/communication-handler-policy.json \
    --region $AWS_REGION

echo "✅ Successfully updated IAM role policy"

# Verify the updated policy
echo "🔍 Verifying updated policy..."
aws iam get-role-policy \
    --role-name $ROLE_NAME \
    --policy-name $POLICY_NAME \
    --region $AWS_REGION \
    --query 'PolicyDocument.Statement[1].Action' \
    --output table

# Clean up
rm /tmp/communication-handler-policy.json

echo ""
echo "🎉 Communication Handler Permissions Fixed!"
echo ""
echo "📋 Summary:"
echo "   Role Name:     $ROLE_NAME"
echo "   Policy Name:   $POLICY_NAME"
echo "   Region:        $AWS_REGION"
echo ""
echo "✅ Added Permissions:"
echo "   📊 DynamoDB: GetItem, PutItem, UpdateItem, DeleteItem, Query, Scan"
echo "   📊 Tables: oscar-agent-context, oscar-agent-sessions"
echo ""
echo "🧪 Test the fix:"
echo "   python3 test_delayed_context_retrieval.py"
echo ""
echo "📝 The communication handler can now:"
echo "   ✅ Store cross-channel context in DynamoDB"
echo "   ✅ Enable follow-up conversations on bot messages"
echo "   ✅ Preserve context across different channels"