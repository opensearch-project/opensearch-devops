# OSCAR - OpenSearch Conversational Automation for Releases

OSCAR is an AI-powered assistant for OpenSearch release management, leveraging Amazon Bedrock for knowledge base integration and Slack for user interaction.

## Components

- **Slack Bot**: AI-powered Slack bot with thread-based context and knowledge base integration
- **CDK Infrastructure**: Modular AWS CDK stacks for deploying the required infrastructure
- **API Gateway**: HTTP endpoint that receives events from Slack and forwards them to Lambda
- **Knowledge Base**: Amazon Bedrock knowledge base with OpenSearch documentation

## Features

- **Thread-Based Context**: Maintains conversation context within Slack threads
- **Knowledge Base Integration**: Uses Amazon Bedrock to query OpenSearch documentation
- **Emoji Reactions**: Provides visual feedback on message processing status
- **Deduplication**: Prevents duplicate responses to the same message
<!-- - **Throttling**: Rate limits requests to prevent overuse -->
- **Toggleable DM Support**: Enable or disable direct message functionality

## Deployment

OSCAR is deployed using AWS CDK:

### Deployment Commands

```bash
# Deploy using settings from .env file
./deploy_cdk.sh

# Deploy with DM functionality explicitly enabled
./deploy_cdk.sh --enable-dm

# Deploy with debug output
./deploy_cdk.sh --debug

# Perform a dry run without making changes
./deploy_cdk.sh --dry-run

# Update just the Lambda function
./deploy_lambda.sh
```

## Configuration

OSCAR uses a hybrid configuration approach for optimal security and maintainability:

### Environment Variables (.env file)
**For sensitive data and large text configurations:**

| Variable | Description | Required |
|----------|-------------|----------|
| `SLACK_BOT_TOKEN` | Slack bot token | Yes |
| `SLACK_SIGNING_SECRET` | Slack signing secret | Yes |
| `KNOWLEDGE_BASE_ID` | Bedrock knowledge base ID | Yes |
| `AWS_REGION` | AWS region | Yes |
| `PROMPT_TEMPLATE` | Custom prompt template (optional) | No |

### CDK Context Configuration (cdk/cdk.context.json)
**For infrastructure and bot behavior settings:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `stage` | Deployment stage (Dev/Beta/Prod) | Dev |
| `model_arn` | Bedrock model ARN | Claude 3.5 Sonnet |
| `lambda_function_name` | Lambda function name | oscar-slack-bot |
| `sessions_table_name` | DynamoDB sessions table | oscar-sessions-v2 |
| `context_table_name` | DynamoDB context table | oscar-context |
| `lambda_timeout` | Lambda timeout (seconds) | 120 |
| `lambda_memory` | Lambda memory (MB) | 512 |
| `max_context_length` | Maximum context length | 5000 |
| `context_summary_length` | Context summary length | 1000 |
| `enable_dm` | Enable direct messages | false |

### Configuration Benefits
- **Security**: Secrets stay in environment variables, never in version control
- **Flexibility**: Infrastructure settings in context files for easy environment management
- **Best Practices**: Follows CDK recommended patterns for configuration management

### Important Notes

**Region Compatibility**: The AWS region must match across all components:
- `.env` file: `AWS_REGION=us-west-2`
- Context file: `model_arn` must use the same region
- Bedrock knowledge base must exist in the same region

**Enhanced Context Preservation**: Recent improvements include:
- **Better AI Model**: Uses Claude 3.5 Sonnet for improved response quality
- **Larger Context**: Increased context limits (5000 chars) for better conversation continuity
- **Improved Summaries**: Enhanced context summarization (1000 chars) for richer thread context
- **Longer Timeout**: Extended Lambda timeout (120s) to accommodate the more capable model

## Usage

### Channel Mentions

Mention the bot in any channel:
```
@oscar What's the status of OpenSearch 2.11?
```

Reply in thread to maintain context:
```
@oscar What about security issues?
```

### Direct Messages (if enabled)

Send a direct message to the bot:
```
What's new in the latest release?
```

## Development

For detailed information about the Slack bot implementation, see the [slack-bot README](slack-bot/README.md).

### Running Tests

```bash
cd slack-bot
chmod +x tests/run_tests.sh
./tests/run_tests.sh
```

## Project Structure

```
├── cdk/                    # CDK infrastructure code
│   ├── stacks/             # CDK stack definitions
│   ├── tests/              # CDK unit tests
│   ├── app.py              # CDK app entry point
│   └── cdk.json            # CDK configuration
├── slack-bot/              # Slack bot implementation
│   ├── tests/              # Unit tests
│   ├── app.py              # Lambda handler
│   ├── bedrock.py          # Bedrock integration
│   ├── config.py           # Configuration management
│   ├── slack_handler.py    # Slack event handling
│   └── storage.py          # DynamoDB storage
├── deploy_cdk.sh           # CDK deployment script
└── deploy_lambda.sh        # Lambda update script
```

## License

This project is licensed under the Apache License 2.0.