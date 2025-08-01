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

- **OscarSlackBotStack** (`slack_bot_stack.py`): Main stack that combines all components
- **OscarStorageStack** (`storage_stack.py`): DynamoDB tables for data storage
- **OscarLambdaStack** (`lambda_stack.py`): Lambda function and API Gateway for request processing

## Lambda Code Customization

The Lambda function code is located in the `lambda/` directory and can be easily customized:

### Default Implementation
- **File**: `lambda/app.py`
- **Purpose**: Contains a placeholder Lambda handler that returns a success response
- **Handler**: `app.lambda_handler`

### Customizing the Lambda Code
To deploy your own Lambda code (such as the full OSCAR Slack bot implementation):

1. **Replace the placeholder code**: Edit or replace `lambda/app.py` with your implementation
2. **Add dependencies**: Update `lambda/requirements.txt` with any required Python packages
3. **Maintain the handler signature**: Ensure your main function is named `lambda_handler` and accepts `(event, context)` parameters
4. **Redeploy**: Run the deployment script to update the Lambda function

Example:
```python
# lambda/app.py
def lambda_handler(event, context):
    # Your custom implementation here
    return {
        'statusCode': 200,
        'body': 'Your custom response'
    }
```

This approach provides maximum flexibility while maintaining a simple deployment process.

## Security Configuration

### CORS (Cross-Origin Resource Sharing)
The API Gateway is configured with secure CORS settings by default:

- **Default allowed origins**: Slack domains (`https://slack.com`, `https://*.slack.com`, `https://api.slack.com`)
- **Allowed methods**: POST only (required for Slack events)
- **Allowed headers**: Content-Type, X-Slack-Request-Timestamp, X-Slack-Signature

To add additional origins (e.g., for testing or custom integrations):
```bash
# In your .env file
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://another-domain.com
```

**Security Note**: Only add trusted domains to avoid potential security vulnerabilities.

## Configuration

OSCAR uses a hybrid configuration approach following CDK best practices:

### Environment Variables (.env file)
**For sensitive data only:**
- `SLACK_BOT_TOKEN`: Bot token from your Slack app
- `SLACK_SIGNING_SECRET`: Signing secret from your Slack app  
- `KNOWLEDGE_BASE_ID`: ID of your Amazon Bedrock knowledge base
- `AWS_REGION`: AWS region for deployment
- `PROMPT_TEMPLATE`: Custom prompt template (optional, for large text)

### CDK Context Configuration (cdk.context.json)
**For infrastructure and behavior settings:**
- `stage`: Deployment stage (Dev/Beta/Prod)
- `model_arn`: Bedrock model ARN (default: Claude 3.5 Sonnet)
- `lambda_function_name`: Lambda function name
- `sessions_table_name`: DynamoDB sessions table name
- `context_table_name`: DynamoDB context table name
- `lambda_timeout`: Lambda timeout in seconds (default: 120)
- `lambda_memory`: Lambda memory in MB (default: 512)
- `max_context_length`: Maximum context length (default: 5000)
- `context_summary_length`: Context summary length (default: 1000)
- `enable_dm`: Enable direct messages (default: false)
- `cors_allowed_origins`: Additional CORS origins

### Configuration Benefits
- **Security**: Secrets never stored in version control
- **Maintainability**: Infrastructure settings easily managed per environment
- **Best Practices**: Follows CDK recommended configuration patterns
- **Deployment Safety**: Context validation prevents misconfiguration

### Recent Improvements

**Enhanced Context Preservation**: The latest version includes significant improvements:
- **Better AI Model**: Upgraded to Claude 3.5 Sonnet for improved response quality
- **Larger Context**: Increased context limits (5000 chars) for better conversation continuity  
- **Enhanced Summaries**: Improved context summarization (1000 chars) for richer thread context
- **Extended Timeout**: Longer Lambda timeout (120s) to accommodate the more capable model
- **Robust Configuration**: Context-based configuration prevents deployment issues

### Region Configuration

**Critical**: All AWS resources must be in the same region:
- `.env` file: `AWS_REGION=us-west-2`
- Context file: `model_arn` must use the same region
- Bedrock knowledge base must exist in the same region

**Configuration Precedence**:
1. CDK context values (recommended)
2. Environment variables from `.env` file  
3. Default values in code

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

- **cdk.json**: Contains CDK app configuration and feature flags
- **cdk.context.json**: Contains environment-specific context values (infrastructure settings)
- **requirements.txt**: Python dependencies for the CDK application
- **CONTEXT_CONFIG.md**: Comprehensive guide to context configuration options

### Context Configuration Guide

For detailed information about all available context parameters, see [CONTEXT_CONFIG.md](CONTEXT_CONFIG.md). This guide includes:
- Complete parameter reference with descriptions and valid values
- Configuration examples for different deployment stages
- Best practices for managing configuration across environments