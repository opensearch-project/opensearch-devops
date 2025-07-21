# OSCAR CDK Deployment

This directory contains the AWS Cloud Development Kit (CDK) code for deploying the OSCAR Slack bot infrastructure.

## Architecture

The CDK deployment creates a modular, serverless architecture for the OSCAR Slack bot with the following components:

### Storage Resources
- **DynamoDB Tables**:
  - `oscar-sessions-v2`: Stores deduplication data and throttling counters with 5-minute TTL
  - `oscar-context`: Stores conversation context with 7-day TTL (604800 seconds)

### Serverless Compute
- **Lambda Function**: Processes Slack events and interacts with the knowledge base
- **API Gateway**: HTTP endpoint for receiving Slack events

### Security
- **IAM Roles**: Provides least-privilege permissions for all components
- **Encryption**: AWS-managed encryption for DynamoDB tables

## Stack Organization

The CDK code is organized into modular stacks for better maintainability:

- **OscarSlackBotStack** (`oscar_slack_bot_stack.py`): Main stack that combines all components
- **OscarStorageStack** (`storage_stack.py`): DynamoDB tables for data storage
- **OscarLambdaStack** (`lambda_stack.py`): Lambda function and API Gateway for request processing

## Environment Variables

The deployment uses the following environment variables, which can be set in a `.env` file in the root directory:

### Required Variables
- `KNOWLEDGE_BASE_ID`: ID of your Amazon Bedrock knowledge base
- `MODEL_ARN`: ARN of the Bedrock model to use (default: Claude 3.5 Haiku)
- `SLACK_BOT_TOKEN`: Bot token from your Slack app
- `SLACK_SIGNING_SECRET`: Signing secret from your Slack app

### Optional Variables
- `AWS_REGION`: AWS region (default: us-east-1)
- `SESSIONS_TABLE_NAME`: Name of the DynamoDB table for sessions (default: "oscar-sessions-v2")
- `CONTEXT_TABLE_NAME`: Name of the DynamoDB table for context (default: "oscar-context")
- `DEDUP_TTL`: Time-to-live for deduplication records in seconds (default: 300)
- `SESSION_TTL`: Time-to-live for session records in seconds (default: 3600)
- `CONTEXT_TTL`: Time-to-live for context records in seconds (default: 604800)
- `MAX_CONTEXT_LENGTH`: Maximum length of context summary (default: 3000)
- `CONTEXT_SUMMARY_LENGTH`: Length of context summary for each interaction (default: 500)
- `ENABLE_DM`: Enable direct message functionality (default: false)
- `PROMPT_TEMPLATE`: Custom prompt template for the Bedrock model
- `ENVIRONMENT`: Deployment environment (default: dev)
- `LAMBDA_FUNCTION_NAME`: Name of the Lambda function (default: oscar-slack-bot)

### Region Configuration

**Important**: The AWS region used for infrastructure deployment must be compatible with your Bedrock resources. Specifically:

1. The region where your Bedrock knowledge base exists must match the `AWS_REGION` environment variable
2. The region in your `MODEL_ARN` must match the region where the model is available

For example, if your knowledge base is in `us-west-2`, you should set:
```
AWS_REGION=us-west-2
MODEL_ARN=arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0
```

### Configuration Precedence

When determining which AWS region to use, the deployment script follows this order of precedence:

1. Command-line arguments (`--region` flag) - highest priority
2. Environment variables from `.env` file (`AWS_REGION` or `AWS_DEFAULT_REGION`)
3. Region extracted from `MODEL_ARN` environment variable
4. Default region specified in code (us-east-1) - lowest priority

This allows you to override the region at different levels depending on your needs.

### Region Configuration

**Important**: The AWS region used for infrastructure deployment and the region where your Bedrock knowledge base is located must be compatible:

- The region specified in `AWS_REGION` should match the region in your `MODEL_ARN` and the region where your knowledge base is created
- If these regions don't match, the Lambda function will not be able to access the knowledge base
- You can deploy infrastructure in one region while using Bedrock resources from another region by explicitly setting `AWS_REGION` in your `.env` file

### Configuration Precedence

The deployment script uses the following precedence to determine configuration values (highest to lowest):

1. Command-line arguments to `deploy_cdk.sh` (e.g., `--region`, `--account`)
2. Environment variables from `.env` file
3. Values extracted from other settings (e.g., region from `MODEL_ARN`)
4. Default values in code

## Deployment Instructions

### Using the Deployment Script

The easiest way to deploy is using the provided script:

```bash
# From the root directory
./deploy_cdk.sh
```

This script will:
1. Load environment variables from `.env`
2. Run tests to ensure everything is working correctly
3. Bootstrap the CDK environment if needed
4. Deploy all required AWS resources
5. Update the Lambda function with the full code

### Command Line Options

The `deploy_cdk.sh` script supports the following options:

- `-a, --account ACCOUNT_ID`: AWS Account ID (default: extracted from .env)
- `-r, --region REGION`: AWS Region (default: extracted from .env)
- `--enable-dm`: Enable direct message functionality (overrides .env setting)
- `-h, --help`: Show help message

## Testing

The CDK code includes unit tests to verify the infrastructure definition:

```bash
# Run the tests
cd cdk
./tests/run_tests.sh
```

The tests verify:
- DynamoDB table creation with correct properties
- Lambda function creation with correct configuration
- API Gateway creation with correct endpoints
- IAM role creation with appropriate permissions

## Configuration

### Slack App Configuration

After deployment, you'll need to configure your Slack app:

1. Go to your Slack App configuration at https://api.slack.com/apps
2. Select your OSCAR app
3. Go to "Event Subscriptions"
4. Toggle "Enable Events" to On
5. Enter the webhook URL from the deployment output as the Request URL
6. Under "Subscribe to bot events", add:
   - `app_mention`
   - `message.im` (if DM functionality is enabled)
7. Click "Save Changes"

## Troubleshooting

### Common Issues

1. **Lambda Function Errors**:
   - Check CloudWatch Logs for detailed error messages
   - Verify that all environment variables are set correctly

2. **Slack Integration Issues**:
   - Verify the webhook URL is correctly configured in Slack
   - Check that all required scopes are added to the Slack app
   - Ensure the bot has been invited to the channel

3. **Knowledge Base Issues**:
   - Verify that the KNOWLEDGE_BASE_ID environment variable is set correctly
   - Check that the knowledge base exists and is active

### Debugging

To debug deployment issues:

```bash
# Get detailed logs during deployment
cdk deploy --debug

# Check Lambda logs
aws logs filter-log-events --log-group-name /aws/lambda/oscar-slack-bot
```

## Clean Up

To remove all deployed resources:

```bash
# Using CDK
cd cdk
cdk destroy
```

## Configuration Files

- **cdk.json**: Contains CDK app configuration and context values
- **cdk.context.json**: Contains environment-specific context values like region
- **requirements.txt**: Python dependencies for the CDK application