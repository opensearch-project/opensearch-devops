#!/bin/bash

# Exit on error
set -e

# Enable debug mode with -d flag
DEBUG=false

# Display usage information
function show_usage {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -a, --account ACCOUNT_ID   AWS Account ID (default: extracted from .env)"
    echo "  -r, --region REGION        AWS Region (default: extracted from .env)"
    echo "  --enable-dm                Enable direct message functionality (default: disabled)"
    echo "  -d, --debug                Enable debug output"
    echo "  --dry-run                  Show what would be done without making changes"
    echo "  -h, --help                 Show this help message"
    exit 1
}

# Error handling function
function handle_error {
    echo "ERROR: $1"
    exit 1
}

# Log function that respects debug mode
function log {
    if [ "$DEBUG" = true ] || [ "$1" != "DEBUG" ]; then
        # Remove DEBUG prefix if in debug mode
        if [ "$DEBUG" = true ] && [ "$1" = "DEBUG" ]; then
            shift
        fi
        echo "$@"
    fi
}

# Parse command line arguments
AWS_ACCOUNT_ID=""
AWS_REGION=""
ENABLE_DM_FLAG=""  # This will track if --enable-dm flag was explicitly provided
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -a|--account)
            AWS_ACCOUNT_ID="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        --enable-dm)
            ENABLE_DM_FLAG="true"
            shift
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Determine ENABLE_DM value from .env file if not provided via command line
if [ -z "$ENABLE_DM_FLAG" ]; then
    # Check for .env file in root directory first, then in slack-bot directory
    if [ -f ".env" ]; then
        ENV_FILE=".env"
    elif [ -f "slack-bot/.env" ]; then
        ENV_FILE="slack-bot/.env"
    else
        ENV_FILE=""
    fi
    
    if [ -n "$ENV_FILE" ]; then
        # Load all environment variables from .env file
        echo "Loading environment variables from $ENV_FILE"
        
        # Export all variables from .env file
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            if [[ ! "$line" =~ ^[[:space:]]*# && -n "$line" ]]; then
                # Extract variable name and value
                var_name=$(echo "$line" | cut -d= -f1)
                var_value=$(echo "$line" | cut -d= -f2-)
                
                # Export the variable
                export "$var_name"="$var_value"
                echo "Exported $var_name from $ENV_FILE"
            fi
        done < "$ENV_FILE"
        
        # Extract ENABLE_DM specifically for command line override
        ENV_ENABLE_DM=$(grep -i "^ENABLE_DM=" $ENV_FILE | cut -d= -f2)
        if [ "$ENV_ENABLE_DM" = "true" ]; then
            ENABLE_DM="true"
        else
            ENABLE_DM="false"
        fi
        echo "Using ENABLE_DM=$ENABLE_DM from $ENV_FILE"
    else
        # Default to false if no .env file found
        ENABLE_DM="false"
    fi
else
    # Use the value from command line flag
    ENABLE_DM="$ENABLE_DM_FLAG"
fi

echo "=== OSCAR Slack Bot CDK Deployment ==="
echo "DM functionality: $([ "$ENABLE_DM" == "true" ] && echo "enabled" || echo "disabled")"

# Export ENABLE_DM for the Lambda function
export ENABLE_DM

# Check for required tools
function check_required_tools {
    log "Checking for required tools..."
    
    if ! command -v aws &> /dev/null; then
        handle_error "AWS CLI is not installed. Please install it first."
    fi
    log "DEBUG AWS CLI is installed"
    
    if ! command -v cdk &> /dev/null; then
        log "Installing AWS CDK..."
        if [ "$DRY_RUN" = false ]; then
            npm install -g aws-cdk || handle_error "Failed to install AWS CDK"
        else
            log "DRY RUN: Would install AWS CDK"
        fi
    fi
    log "DEBUG CDK is installed"
    
    if ! command -v python3 &> /dev/null; then
        handle_error "Python 3 is not installed. Please install it first."
    fi
    log "DEBUG Python 3 is installed"
}

# Load environment variables from .env file
function load_env_file {
    local env_file=$1
    log "Loading environment variables from $env_file"
    
    if [ ! -f "$env_file" ]; then
        handle_error "Environment file $env_file not found"
    fi
    
    # Export all variables from .env file
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        if [[ ! "$line" =~ ^[[:space:]]*# && -n "$line" ]]; then
            # Extract variable name and value
            var_name=$(echo "$line" | cut -d= -f1)
            var_value=$(echo "$line" | cut -d= -f2-)
            
            # Export the variable
            export "$var_name"="$var_value"
            log "DEBUG Exported $var_name from $env_file"
        fi
    done < "$env_file"
}

# Find and load the appropriate .env file
function find_and_load_env_file {
    local env_file=""
    
    # Check for .env file in root directory first, then in slack-bot directory
    if [ -f ".env" ]; then
        env_file=".env"
    elif [ -f "slack-bot/.env" ]; then
        env_file="slack-bot/.env"
    else
        handle_error ".env file not found in root or slack-bot directory and no account/region provided.
Please provide AWS account ID and region as command-line arguments or create the .env file."
    fi
    
    load_env_file "$env_file"
    return 0
}

# Extract AWS account and region information
function extract_aws_info {
    log "Extracting AWS account and region information..."
    
    # If account ID not provided, try to extract from environment
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        # First try to read AWS_ACCOUNT_ID directly from environment
        if [ -n "$AWS_ACCOUNT_ID" ]; then
            log "Using AWS Account ID from environment: $AWS_ACCOUNT_ID"
        else
            # Fall back to extracting from MODEL_ARN if AWS_ACCOUNT_ID not found
            if [ -n "$MODEL_ARN" ]; then
                AWS_ACCOUNT_ID=$(echo $MODEL_ARN | sed -n 's/.*:bedrock:\([^:]*\):\([^:]*\):.*/\2/p')
                log "Using AWS Account ID from MODEL_ARN: $AWS_ACCOUNT_ID"
            fi
        fi
    else
        log "Using provided AWS Account ID: $AWS_ACCOUNT_ID"
    fi
    
    # If region not provided, try to extract from environment
    if [ -z "$AWS_REGION" ]; then
        # First try to read AWS_REGION directly from environment
        if [ -n "$AWS_REGION" ]; then
            log "Using AWS Region from environment: $AWS_REGION"
        else
            # Fall back to extracting from MODEL_ARN
            if [ -n "$MODEL_ARN" ]; then
                AWS_REGION=$(echo $MODEL_ARN | sed -n 's/.*:bedrock:\([^:]*\):.*/\1/p')
                log "Using AWS Region from MODEL_ARN: $AWS_REGION"
            else
                # Default to us-east-1 if no region found
                AWS_REGION="us-east-1"
                log "No region found, defaulting to: $AWS_REGION"
            fi
        fi
    else
        log "Using provided AWS Region: $AWS_REGION"
    fi
    
    # Validate account ID and region
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        handle_error "AWS Account ID is required. Please provide it as a command-line argument or in the .env file."
    fi
    
    if [ -z "$AWS_REGION" ]; then
        handle_error "AWS Region is required. Please provide it as a command-line argument or in the .env file."
    fi
}

# Check required tools
check_required_tools

# If account ID or region not provided, extract from .env file
if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ]; then
    find_and_load_env_file
fi

# Extract AWS account and region information
extract_aws_info

# Export MODEL_ARN and KNOWLEDGE_BASE_ID for the stack if not already set
if [ -z "$MODEL_ARN" ]; then
    export MODEL_ARN="arn:aws:bedrock:$AWS_REGION::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
    log "WARNING: MODEL_ARN not set, using default: $MODEL_ARN"
fi

if [ -z "$KNOWLEDGE_BASE_ID" ]; then
    export KNOWLEDGE_BASE_ID="PLACEHOLDER_KNOWLEDGE_BASE_ID"
    log "WARNING: KNOWLEDGE_BASE_ID not set, using placeholder value"
fi

log "Using Knowledge Base ID: $KNOWLEDGE_BASE_ID"
log "Using Model ARN: $MODEL_ARN"

# Validate account ID and region
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: AWS Account ID is required. Please provide it as a command-line argument or in the .env file."
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo "Error: AWS Region is required. Please provide it as a command-line argument or in the .env file."
    exit 1
fi

# Export for CDK
export CDK_DEFAULT_ACCOUNT=$AWS_ACCOUNT_ID
export CDK_DEFAULT_REGION=$AWS_REGION

# Update region in cdk.json context
log "Updating CDK context with region: $AWS_REGION"
if [ "$DRY_RUN" = false ]; then
    # Use jq to update the region in cdk.json if jq is available
    if command -v jq &> /dev/null; then
        jq --arg region "$AWS_REGION" '.context."aws:cdk:toolkit:default-region" = $region' cdk/cdk.json > cdk/cdk.json.tmp && mv cdk/cdk.json.tmp cdk/cdk.json
        log "Updated region in cdk/cdk.json using jq"
    else
        # Fallback to sed if jq is not available
        log "jq not found, using sed to update region in cdk/cdk.json"
        # Create a backup of the original file
        cp cdk/cdk.json cdk/cdk.json.bak
        # Use sed to replace the region value
        sed -i.bak "s/\"aws:cdk:toolkit:default-region\": \"[^\"]*\"/\"aws:cdk:toolkit:default-region\": \"$AWS_REGION\"/" cdk/cdk.json
        # Remove backup files
        rm -f cdk/cdk.json.bak
    fi
else
    log "DRY RUN: Would update region to $AWS_REGION in cdk/cdk.json"
fi

# Create and activate virtual environment for CDK
log "Setting up Python virtual environment..."
if [ "$DRY_RUN" = false ]; then
    python -m venv .venv || handle_error "Failed to create virtual environment"
    source .venv/bin/activate || handle_error "Failed to activate virtual environment"
else
    log "DRY RUN: Would create and activate Python virtual environment"
fi

# Install CDK dependencies
log "Installing CDK dependencies..."
if [ "$DRY_RUN" = false ]; then
    pip install -r cdk/requirements.txt || handle_error "Failed to install CDK dependencies"
else
    log "DRY RUN: Would install dependencies from cdk/requirements.txt"
fi

# Create build_docs directory if it doesn't exist
log "Creating build_docs directory..."
if [ "$DRY_RUN" = false ]; then
    mkdir -p build_docs
    echo "# Sample Documentation" > build_docs/sample.md
    echo "This is a sample document for the knowledge base." >> build_docs/sample.md
else
    log "DRY RUN: Would create build_docs directory with sample documentation"
fi

# Run tests before deployment
log "Running tests for OSCAR Slack Bot..."
if [ -f "slack-bot/tests/run_tests.sh" ]; then
    # Install test dependencies
    log "Installing test dependencies..."
    if [ "$DRY_RUN" = false ]; then
        pip install pytest pytest-cov slack_bolt boto3 moto || log "WARNING: Failed to install some test dependencies"
    else
        log "DRY RUN: Would install test dependencies"
    fi
    
    # Run tests
    if [ "$DRY_RUN" = false ]; then
        chmod +x slack-bot/tests/run_tests.sh
        cd slack-bot
        ./tests/run_tests.sh
        SLACK_BOT_TEST_EXIT_CODE=$?
        cd ..
        
        # Check if tests passed
        if [ $SLACK_BOT_TEST_EXIT_CODE -eq 0 ]; then
            log "Slack bot tests completed successfully!"
        else
            log "WARNING: Some slack bot tests failed, but continuing with deployment."
        fi
    else
        log "DRY RUN: Would run slack-bot tests"
    fi
else
    log "WARNING: Slack bot test script not found, skipping tests"
fi

# Run CDK tests
log "Running tests for CDK infrastructure..."
if [ -f "cdk/tests/run_tests.sh" ]; then
    if [ "$DRY_RUN" = false ]; then
        chmod +x cdk/tests/run_tests.sh
        cd cdk
        ./tests/run_tests.sh
        CDK_TEST_EXIT_CODE=$?
        cd ..
        
        # Check if tests passed
        if [ $CDK_TEST_EXIT_CODE -eq 0 ]; then
            log "CDK tests completed successfully!"
        else
            log "WARNING: Some CDK tests failed, but continuing with deployment."
        fi
    else
        log "DRY RUN: Would run CDK tests"
    fi
else
    log "WARNING: CDK test script not found, skipping tests"
fi

# Bootstrap CDK (if not already done)
log "Bootstrapping CDK environment..."
if [ "$DRY_RUN" = false ]; then
    cd cdk
    AWS_REGION=$AWS_REGION AWS_DEFAULT_REGION=$AWS_REGION cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION --force || handle_error "Failed to bootstrap CDK environment"
    cd ..
else
    log "DRY RUN: Would bootstrap CDK environment for account $AWS_ACCOUNT_ID in region $AWS_REGION"
fi

# Deploy the stack
log "Deploying OSCAR Slack Bot stack..."
if [ "$DRY_RUN" = false ]; then
    cd cdk
    AWS_REGION=$AWS_REGION AWS_DEFAULT_REGION=$AWS_REGION cdk deploy --require-approval never || handle_error "Failed to deploy CDK stack"
    cd ..
else
    log "DRY RUN: Would deploy CDK stack"
fi

# Get outputs
if [ "$DRY_RUN" = false ]; then
    log "Getting deployment outputs..."
    LAMBDA_FUNCTION_NAME=$(AWS_DEFAULT_REGION=$AWS_REGION aws cloudformation describe-stacks --stack-name OscarSlackBotStack --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionName'].OutputValue" --output text --region $AWS_REGION)
    WEBHOOK_URL=$(AWS_DEFAULT_REGION=$AWS_REGION aws cloudformation describe-stacks --stack-name OscarSlackBotStack --query "Stacks[0].Outputs[?contains(OutputKey, 'SlackWebhookUrl')].OutputValue" --output text --region $AWS_REGION)

    # If webhook URL is empty, try alternative output key pattern
    if [ -z "$WEBHOOK_URL" ]; then
        WEBHOOK_URL=$(AWS_DEFAULT_REGION=$AWS_REGION aws cloudformation describe-stacks --stack-name OscarSlackBotStack --query "Stacks[0].Outputs[?contains(OutputKey, 'LambdaStackSlackWebhookUrl')].OutputValue" --output text --region $AWS_REGION)
    fi
    
    # If still empty, try the new output key
    if [ -z "$WEBHOOK_URL" ]; then
        WEBHOOK_URL=$(AWS_DEFAULT_REGION=$AWS_REGION aws cloudformation describe-stacks --stack-name OscarSlackBotStack --query "Stacks[0].Outputs[?OutputKey=='SlackBotApiUrl'].OutputValue" --output text --region $AWS_REGION)
        if [ -n "$WEBHOOK_URL" ]; then
            WEBHOOK_URL="${WEBHOOK_URL}slack/events"
        fi
    fi
else
    log "DRY RUN: Would get deployment outputs"
    LAMBDA_FUNCTION_NAME="oscar-slack-bot"
    WEBHOOK_URL="https://example.execute-api.${AWS_REGION}.amazonaws.com/prod/slack/events"
fi

# Update the Lambda function with the full code
log "Updating Lambda function with full code..."
if [ "$DRY_RUN" = false ]; then
    # Pass the ENABLE_DM variable explicitly to deploy_lambda.sh
    ENABLE_DM=$ENABLE_DM LAMBDA_FUNCTION_NAME=$LAMBDA_FUNCTION_NAME AWS_REGION=$AWS_REGION ./deploy_lambda.sh || handle_error "Failed to update Lambda function code"
else
    log "DRY RUN: Would update Lambda function $LAMBDA_FUNCTION_NAME with full code"
fi

log "Deployment complete!"
echo ""
echo "=============================================================="
echo "                   SLACK BOT REQUEST URL                       "
echo "=============================================================="
echo "$WEBHOOK_URL"
echo "=============================================================="
echo ""
echo "=== Configuration Steps ==="
echo "1. Configure Slack App:"
echo "   - Go to https://api.slack.com/apps"
echo "   - Create a new app or update your existing app"
echo "   - Under 'Event Subscriptions', enable events and set the Request URL to the URL above"
echo "   - Subscribe to 'app_mention' and 'message.im' events"
echo "   - Under 'OAuth & Permissions', add the required scopes:"
echo "     * app_mentions:read"
echo "     * chat:write"
echo "     * channels:history"
echo "     * im:history"
echo "   - Install the app to your workspace"
echo ""
echo "2. Test your bot by mentioning it in a channel or sending a direct message"

# Deactivate virtual environment
if [ "$DRY_RUN" = false ]; then
    deactivate
fi