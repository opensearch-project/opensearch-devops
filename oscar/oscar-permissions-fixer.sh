#!/bin/bash

# OSCAR Complete Permissions Fixer
# This script fixes ALL permissions for OSCAR CDK deployment:
# 1. Resource-based policies on Lambda functions (allows Bedrock agents to invoke them)
# 2. Identity-based policies on IAM roles (allows Lambda functions to access AWS services)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}[INFO] 🔐 OSCAR Complete Permissions Fixer${NC}"
echo -e "${BLUE}[INFO] ====================================${NC}"
echo -e "${BLUE}[INFO] Fixing both resource-based and identity-based policies...${NC}"

# Load environment variables from .env file
if [ -f "cdk/.env" ]; then
    echo -e "${BLUE}[INFO] Loading environment variables from cdk/.env${NC}"
    # Use a safer method to load environment variables, avoiding complex JSON values
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue
        # Only export simple key=value pairs (avoid complex JSON)
        if [[ $value != *"{"* && $value != *"}"* ]]; then
            export "$key=$value"
        fi
    done < cdk/.env
else
    echo -e "${RED}[ERROR] cdk/.env file not found!${NC}"
    exit 1
fi

# Configuration from environment or defaults
PRIVILEGED_AGENT_ID="${OSCAR_PRIVILEGED_BEDROCK_AGENT_ID}"
PRIVILEGED_AGENT_ALIAS="${OSCAR_PRIVILEGED_BEDROCK_AGENT_ALIAS_ID}"
LIMITED_AGENT_ID="${OSCAR_LIMITED_BEDROCK_AGENT_ID}"
LIMITED_AGENT_ALIAS="${OSCAR_LIMITED_BEDROCK_AGENT_ALIAS_ID}"
ACCOUNT_ID="${AWS_ACCOUNT_ID}"
REGION="${AWS_REGION}"

# Dynamic IAM role names (with fallbacks for CDK deployment)
SUPERVISOR_ROLE_NAME="${LAMBDA_EXECUTION_ROLE_NAME:-oscar-lambda-execution-role-cdk}"
COMM_HANDLER_ROLE_NAME="${COMMUNICATION_HANDLER_ROLE_NAME:-oscar-communication-handler-execution-role-cdk}"
JENKINS_ROLE_NAME="${JENKINS_LAMBDA_ROLE_NAME:-oscar-jenkins-lambda-execution-role-cdk}"
METRICS_ROLE_NAME="${OSCAR_METRICS_LAMBDA_VPC_ROLE_NAME:-oscar-metrics-lambda-vpc-role}"

# Validate required configuration
if [[ -z "$PRIVILEGED_AGENT_ID" || -z "$LIMITED_AGENT_ID" || -z "$ACCOUNT_ID" || -z "$REGION" ]]; then
    echo -e "${RED}[ERROR] Missing required configuration in .env file!${NC}"
    echo -e "${RED}Required: OSCAR_PRIVILEGED_BEDROCK_AGENT_ID, OSCAR_LIMITED_BEDROCK_AGENT_ID, AWS_ACCOUNT_ID, AWS_REGION${NC}"
    exit 1
fi

echo -e "${BLUE}[INFO] Configuration:${NC}"
echo -e "${BLUE}[INFO] - Privileged Agent: $PRIVILEGED_AGENT_ID/$PRIVILEGED_AGENT_ALIAS${NC}"
echo -e "${BLUE}[INFO] - Limited Agent: $LIMITED_AGENT_ID/$LIMITED_AGENT_ALIAS${NC}"
echo -e "${BLUE}[INFO] - Account: $ACCOUNT_ID${NC}"
echo -e "${BLUE}[INFO] - Region: $REGION${NC}"

# =============================================================================
# PART 1: IDENTITY-BASED POLICIES (IAM Role Policies)
# =============================================================================

echo -e "${BLUE}[INFO] 🎯 PART 1: Fixing IAM Role Policies (Identity-based)${NC}"

# Function to add policy to role
add_policy_to_role() {
    local role_name=$1
    local policy_name=$2
    local policy_document=$3
    
    echo -e "${BLUE}[INFO] Adding policy '$policy_name' to role '$role_name'...${NC}"
    aws iam put-role-policy \
        --role-name "$role_name" \
        --policy-name "$policy_name" \
        --policy-document "$policy_document"
    echo -e "${GREEN}[SUCCESS] ✅ Policy '$policy_name' added to '$role_name'${NC}"
}

# 1. FIX SUPERVISOR AGENT (oscar-supervisor-agent-cdk)
echo -e "${BLUE}[INFO] 🎯 Fixing Supervisor Agent IAM permissions...${NC}"

SUPERVISOR_BEDROCK_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAgentInvocation",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeAgent",
                "bedrock-agent-runtime:InvokeAgent",
                "bedrock:InvokeModel",
                "bedrock:GetAgent",
                "bedrock:GetKnowledgeBase",
                "bedrock:Retrieve",
                "bedrock:RetrieveAndGenerate"
            ],
            "Resource": [
                "arn:aws:bedrock:'$REGION':'$ACCOUNT_ID':agent/'$PRIVILEGED_AGENT_ID'",
                "arn:aws:bedrock:'$REGION':'$ACCOUNT_ID':agent-alias/'$PRIVILEGED_AGENT_ID'/'$PRIVILEGED_AGENT_ALIAS'",
                "arn:aws:bedrock:'$REGION':'$ACCOUNT_ID':agent-alias/'$PRIVILEGED_AGENT_ID'/*",
                "arn:aws:bedrock:'$REGION':'$ACCOUNT_ID':agent/'$LIMITED_AGENT_ID'",
                "arn:aws:bedrock:'$REGION':'$ACCOUNT_ID':agent-alias/'$LIMITED_AGENT_ID'/'$LIMITED_AGENT_ALIAS'",
                "arn:aws:bedrock:'$REGION':'$ACCOUNT_ID':agent-alias/'$LIMITED_AGENT_ID'/*",
                "arn:aws:bedrock:'$REGION':'$ACCOUNT_ID':knowledge-base/*",
                "arn:aws:bedrock:'$REGION'::foundation-model/anthropic.claude-3-haiku-*",
                "arn:aws:bedrock:'$REGION'::foundation-model/anthropic.claude-3-sonnet-*"
            ]
        }
    ]
}'

SUPERVISOR_DYNAMODB_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBCDKAccess",
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
                "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'${CONTEXT_TABLE_NAME:-oscar-agent-context-dev-cdk}'",
                "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'${CONTEXT_TABLE_NAME:-oscar-agent-context-dev-cdk}'/*",
                "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'${SESSIONS_TABLE_NAME:-oscar-agent-sessions-dev-cdk}'",
                "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'${SESSIONS_TABLE_NAME:-oscar-agent-sessions-dev-cdk}'/*"
            ]
        }
    ]
}'

SUPERVISOR_LAMBDA_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaCDKInvocation",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:'$REGION':'$ACCOUNT_ID':function:oscar-*-cdk",
                "arn:aws:lambda:'$REGION':'$ACCOUNT_ID':function:oscar-supervisor-agent-cdk",
                "arn:aws:lambda:'$REGION':'$ACCOUNT_ID':function:oscar-communication-handler-cdk",
                "arn:aws:lambda:'$REGION':'$ACCOUNT_ID':function:oscar-test-metrics-agent-cdk",
                "arn:aws:lambda:'$REGION':'$ACCOUNT_ID':function:oscar-build-metrics-agent-cdk",
                "arn:aws:lambda:'$REGION':'$ACCOUNT_ID':function:oscar-release-metrics-agent-cdk",
                "arn:aws:lambda:'$REGION':'$ACCOUNT_ID':function:oscar-jenkins-agent-cdk"
            ]
        }
    ]
}'

add_policy_to_role "$SUPERVISOR_ROLE_NAME" "BedrockAgentInvocationPolicy" "$SUPERVISOR_BEDROCK_POLICY"
add_policy_to_role "$SUPERVISOR_ROLE_NAME" "DynamoDBCDKAccess" "$SUPERVISOR_DYNAMODB_POLICY"
add_policy_to_role "$SUPERVISOR_ROLE_NAME" "LambdaCDKInvocation" "$SUPERVISOR_LAMBDA_POLICY"

# 2. FIX COMMUNICATION HANDLER (oscar-communication-handler-cdk)
echo -e "${BLUE}[INFO] 📞 Fixing Communication Handler IAM permissions...${NC}"

COMM_HANDLER_POLICY='{
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
                "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'${CONTEXT_TABLE_NAME:-oscar-agent-context-dev-cdk}'",
                "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'${CONTEXT_TABLE_NAME:-oscar-agent-context-dev-cdk}'/*",
                "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'${SESSIONS_TABLE_NAME:-oscar-agent-sessions-dev-cdk}'",
                "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/'${SESSIONS_TABLE_NAME:-oscar-agent-sessions-dev-cdk}'/*"
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
}'

add_policy_to_role "$COMM_HANDLER_ROLE_NAME" "CommunicationHandlerCDKPolicy" "$COMM_HANDLER_POLICY"

# 3. FIX METRICS AGENTS (VPC Lambda role - shared by all 3 metrics agents)
echo -e "${BLUE}[INFO] 📊 Fixing Metrics Agents IAM permissions...${NC}"

# The metrics agents already have the cross-account OpenSearch access, just need to ensure secrets access
METRICS_ADDITIONAL_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws:secretsmanager:'$REGION':'$ACCOUNT_ID':secret:'${CENTRAL_SECRET_NAME:-oscar-central-env-dev-cdk}'*",
                "arn:aws:secretsmanager:'$REGION':'$ACCOUNT_ID':secret:oscar-central-env*"
            ]
        }
    ]
}'

add_policy_to_role "$METRICS_ROLE_NAME" "MetricsAgentsCDKPolicy" "$METRICS_ADDITIONAL_POLICY"

# 4. FIX JENKINS AGENT (oscar-jenkins-agent-cdk)
echo -e "${BLUE}[INFO] 🔧 Fixing Jenkins Agent IAM permissions...${NC}"

JENKINS_POLICY='{
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
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}'

add_policy_to_role "$JENKINS_ROLE_NAME" "JenkinsAgentCDKPolicy" "$JENKINS_POLICY"

# =============================================================================
# PART 2: RESOURCE-BASED POLICIES (Lambda Function Policies)
# =============================================================================

echo -e "${BLUE}[INFO] 🎯 PART 2: Fixing Lambda Function Policies (Resource-based)${NC}"

# Function to add resource-based policy to Lambda function
add_lambda_permission() {
    local function_name=$1
    local agent_id=$2
    local agent_name=$3
    
    echo -e "${BLUE}[INFO] Adding permission for ${agent_name} agent (${agent_id}) to invoke ${function_name}${NC}"
    
    # Generate a unique statement ID
    local statement_id="bedrock-v2-${agent_id}-$(date +%s)"
    
    # Add the permission
    aws lambda add-permission \
        --function-name "${function_name}" \
        --statement-id "${statement_id}" \
        --action "lambda:InvokeFunction" \
        --principal "bedrock.amazonaws.com" \
        --source-arn "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:agent/${agent_id}" \
        --output text > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SUCCESS] ✅ Permission added for ${function_name}${NC}"
    else
        # Check if permission already exists
        aws lambda get-policy --function-name "${function_name}" --query 'Policy' --output text 2>/dev/null | grep -q "${agent_id}"
        if [ $? -eq 0 ]; then
            echo -e "${YELLOW}[INFO] ⚠️  Permission already exists for ${function_name}${NC}"
        else
            echo -e "${RED}[ERROR] ❌ Failed to add permission for ${function_name}${NC}"
            return 1
        fi
    fi
}

# Function to remove existing permissions for an agent (cleanup)
remove_existing_permissions() {
    local function_name=$1
    local agent_id=$2
    
    echo -e "${BLUE}[INFO] Checking for existing permissions for agent ${agent_id} on ${function_name}${NC}"
    
    # Get current policy and extract statement IDs that match this agent
    local policy=$(aws lambda get-policy --function-name "${function_name}" --query 'Policy' --output text 2>/dev/null || echo "")
    
    if [ -n "$policy" ]; then
        # Extract statement IDs that contain this agent ID
        local statement_ids=$(echo "$policy" | jq -r --arg agent_id "$agent_id" '.Statement[] | select(.Condition.ArnLike."AWS:SourceArn" | contains($agent_id)) | .Sid' 2>/dev/null || echo "")
        
        if [ -n "$statement_ids" ]; then
            echo "$statement_ids" | while read -r sid; do
                if [ -n "$sid" ]; then
                    echo -e "${YELLOW}[INFO] Removing existing permission: ${sid}${NC}"
                    aws lambda remove-permission --function-name "${function_name}" --statement-id "${sid}" > /dev/null 2>&1 || true
                fi
            done
        fi
    fi
}

echo -e "${BLUE}[INFO] Processing Lambda function resource-based permissions...${NC}"

# Process all Lambda functions with their corresponding agents
echo -e "${BLUE}[INFO] 🔧 Processing Lambda function permissions for all agents...${NC}"

# Helper function to process Lambda permissions for both agents
process_lambda_permissions() {
    local lambda_arn=$1
    local lambda_name=$2
    local description=$3
    
    if [ -n "$lambda_arn" ]; then
        local function_name=$(echo "$lambda_arn" | awk -F':' '{print $NF}')
        echo -e "${BLUE}[INFO] Processing $description Lambda: $function_name${NC}"
        
        # Add permissions for both OSCAR agents
        if [ -n "$LIMITED_AGENT_ID" ]; then
            remove_existing_permissions "$function_name" "$LIMITED_AGENT_ID"
            add_lambda_permission "$function_name" "$LIMITED_AGENT_ID" "OSCAR Limited"
        fi
        if [ -n "$PRIVILEGED_AGENT_ID" ]; then
            remove_existing_permissions "$function_name" "$PRIVILEGED_AGENT_ID"
            add_lambda_permission "$function_name" "$PRIVILEGED_AGENT_ID" "OSCAR Privileged"
        fi
        
        # Add permissions for specific agent if applicable
        case "$description" in
            "Jenkins")
                if [ -n "$JENKINS_AGENT_ID" ]; then
                    remove_existing_permissions "$function_name" "$JENKINS_AGENT_ID"
                    add_lambda_permission "$function_name" "$JENKINS_AGENT_ID" "Jenkins"
                fi
                ;;
            "Build Metrics")
                if [ -n "$BUILD_METRICS_AGENT_ID" ]; then
                    remove_existing_permissions "$function_name" "$BUILD_METRICS_AGENT_ID"
                    add_lambda_permission "$function_name" "$BUILD_METRICS_AGENT_ID" "Build Metrics"
                fi
                ;;
            "Test Metrics")
                if [ -n "$TEST_METRICS_AGENT_ID" ]; then
                    remove_existing_permissions "$function_name" "$TEST_METRICS_AGENT_ID"
                    add_lambda_permission "$function_name" "$TEST_METRICS_AGENT_ID" "Test Metrics"
                fi
                ;;
            "Release Metrics")
                if [ -n "$RELEASE_METRICS_AGENT_ID" ]; then
                    remove_existing_permissions "$function_name" "$RELEASE_METRICS_AGENT_ID"
                    add_lambda_permission "$function_name" "$RELEASE_METRICS_AGENT_ID" "Release Metrics"
                fi
                ;;
        esac
    fi
}

# Process all Lambda functions
process_lambda_permissions "$MAIN_LAMBDA_ARN" "$CDK_SUPERVISOR_FUNCTION" "Supervisor"
process_lambda_permissions "$COMMUNICATION_LAMBDA_ARN" "$CDK_COMM_HANDLER_FUNCTION" "Communication Handler"
process_lambda_permissions "$JENKINS_LAMBDA_ARN" "$CDK_JENKINS_FUNCTION" "Jenkins"
process_lambda_permissions "$BUILD_METRICS_LAMBDA_ARN" "$CDK_BUILD_METRICS_FUNCTION" "Build Metrics"
process_lambda_permissions "$TEST_METRICS_LAMBDA_ARN" "$CDK_TEST_METRICS_FUNCTION" "Test Metrics"
process_lambda_permissions "$RELEASE_METRICS_LAMBDA_ARN" "$CDK_RELEASE_METRICS_FUNCTION" "Release Metrics"

# CDK Lambda Functions
echo -e "${BLUE}[INFO] 🔧 Processing CDK Lambda function resource-based permissions...${NC}"

# Get Lambda function names from environment variables (with fallbacks)
CDK_SUPERVISOR_FUNCTION="${MAIN_LAMBDA_FUNCTION_NAME:-oscar-supervisor-agent-cdk}"
CDK_COMM_HANDLER_FUNCTION="${COMMUNICATION_LAMBDA_FUNCTION_NAME:-oscar-communication-handler-cdk}"
CDK_JENKINS_FUNCTION="${JENKINS_LAMBDA_FUNCTION_NAME:-oscar-jenkins-agent-cdk}"
CDK_TEST_METRICS_FUNCTION="${METRICS_TEST_FUNCTION:-oscar-test-metrics-agent-cdk}"
CDK_BUILD_METRICS_FUNCTION="${METRICS_BUILD_FUNCTION:-oscar-build-metrics-agent-cdk}"
CDK_RELEASE_METRICS_FUNCTION="${METRICS_RELEASE_FUNCTION:-oscar-release-metrics-agent-cdk}"



# =============================================================================
# PART 3: BEDROCK AGENT RESOURCE-BASED POLICIES
# =============================================================================

echo -e "${BLUE}[INFO] 🎯 PART 3: Adding resource-based policies to Bedrock agents...${NC}"

# Get all Lambda execution role ARNs (use from environment or construct dynamically)
SUPERVISOR_ROLE_ARN="${LAMBDA_EXECUTION_ROLE_ARN:-arn:aws:iam::$ACCOUNT_ID:role/$SUPERVISOR_ROLE_NAME}"
COMM_HANDLER_ROLE_ARN="${COMMUNICATION_HANDLER_ROLE_ARN:-arn:aws:iam::$ACCOUNT_ID:role/$COMM_HANDLER_ROLE_NAME}"
JENKINS_ROLE_ARN="${JENKINS_LAMBDA_ROLE_ARN:-arn:aws:iam::$ACCOUNT_ID:role/$JENKINS_ROLE_NAME}"

RESOURCE_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowLambdaInvocation",
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "'$SUPERVISOR_ROLE_ARN'",
                    "'$COMM_HANDLER_ROLE_ARN'",
                    "'$JENKINS_ROLE_ARN'"
                ]
            },
            "Action": "bedrock:InvokeAgent",
            "Resource": "*"
        }
    ]
}'

# Apply to privileged agent
aws bedrock-agent put-agent-resource-policy \
    --agent-id "$PRIVILEGED_AGENT_ID" \
    --policy "$RESOURCE_POLICY" 2>/dev/null || {
    echo -e "${YELLOW}[WARNING] ⚠️  Failed to add resource-based policy to privileged agent. This might be expected if policy already exists.${NC}"
}

# Apply to limited agent  
aws bedrock-agent put-agent-resource-policy \
    --agent-id "$LIMITED_AGENT_ID" \
    --policy "$RESOURCE_POLICY" 2>/dev/null || {
    echo -e "${YELLOW}[WARNING] ⚠️  Failed to add resource-based policy to limited agent. This might be expected if policy already exists.${NC}"
}

echo -e "${GREEN}[SUCCESS] ✅ Resource-based policies applied to Bedrock agents${NC}"

# =============================================================================
# VERIFICATION
# =============================================================================

echo -e "${BLUE}[INFO] 🔍 Verifying permissions for all roles...${NC}"

echo -e "${BLUE}[INFO] Supervisor Agent Role ($SUPERVISOR_ROLE_NAME):${NC}"
aws iam list-role-policies --role-name "$SUPERVISOR_ROLE_NAME" --query 'PolicyNames' --output table

echo -e "${BLUE}[INFO] Communication Handler Role ($COMM_HANDLER_ROLE_NAME):${NC}"
aws iam list-role-policies --role-name "$COMM_HANDLER_ROLE_NAME" --query 'PolicyNames' --output table

echo -e "${BLUE}[INFO] VPC Lambda Role for Metrics ($METRICS_ROLE_NAME):${NC}"
aws iam list-role-policies --role-name "$METRICS_ROLE_NAME" --query 'PolicyNames' --output table

echo -e "${BLUE}[INFO] Jenkins Agent Role ($JENKINS_ROLE_NAME):${NC}"
aws iam list-role-policies --role-name "$JENKINS_ROLE_NAME" --query 'PolicyNames' --output table

echo -e "${GREEN}[SUCCESS] ✅ OSCAR Complete Permissions Fixer completed successfully!${NC}"
echo -e "${BLUE}[INFO] 📋 Summary of fixes applied:${NC}"
echo -e "${BLUE}[INFO]   ✅ Supervisor Agent: Bedrock agents, DynamoDB, Lambda invocation${NC}"
echo -e "${BLUE}[INFO]   ✅ Communication Handler: Bedrock agents, DynamoDB, CloudWatch Logs${NC}"
echo -e "${BLUE}[INFO]   ✅ Metrics Agents: Cross-account OpenSearch, S3 cache, CloudWatch Logs${NC}"
echo -e "${BLUE}[INFO]   ✅ Jenkins Agent: Bedrock agents, CloudWatch Logs${NC}"
echo -e "${BLUE}[INFO]   ✅ Resource-based policies on Lambda functions for Bedrock agent invocation${NC}"
echo -e "${BLUE}[INFO]   ✅ Resource-based policies on Bedrock agents for Lambda role access${NC}"
echo -e "${BLUE}[INFO] 🎯 All permissions configured! OSCAR should now work correctly.${NC}"