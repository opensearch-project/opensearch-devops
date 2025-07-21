# OSCAR - OpenSearch Conversational Automation for Releases

OSCAR is an AI-powered assistant for OpenSearch release management, leveraging Amazon Bedrock for knowledge base integration and Slack for user interaction.

## Components

- **Slack Bot**: AI-powered Slack bot with thread-based context and knowledge base integration
- **CDK Infrastructure**: Modular AWS CDK stacks for deploying the required infrastructure
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

## Environment Variables

Create a `.env` file in the root directory with the following variables:

### Required Variables

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Slack bot token |
| `SLACK_SIGNING_SECRET` | Slack signing secret |
| `KNOWLEDGE_BASE_ID` | Bedrock knowledge base ID |
| `MODEL_ARN` | Bedrock model ARN |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | us-east-1 |
| `SESSIONS_TABLE_NAME` | DynamoDB sessions table name | oscar-sessions-v2 |
| `CONTEXT_TABLE_NAME` | DynamoDB context table name | oscar-context |
| `DEDUP_TTL` | Deduplication TTL in seconds | 300 (5 minutes) |
| `SESSION_TTL` | Session TTL in seconds | 3600 (1 hour) |
| `CONTEXT_TTL` | Context TTL in seconds | 604800 (7 days) |
| `MAX_CONTEXT_LENGTH` | Maximum context length | 3000 |
| `CONTEXT_SUMMARY_LENGTH` | Context summary length | 500 |
| `ENABLE_DM` | Enable direct messages | false |
| `PROMPT_TEMPLATE` | Custom prompt template | Default template |
<!-- | `THROTTLE_REQUESTS_PER_MINUTE` | Maximum requests per minute per user | 5 |
| `THROTTLE_WINDOW_SECONDS` | Throttling window in seconds | 60 | -->

### Important Notes on Region Configuration

**Region Compatibility**: The AWS region used for the Bedrock knowledge base must match the region specified in your environment variables. If your knowledge base is in `us-west-2`, make sure to set `AWS_REGION=us-west-2` in your `.env` file.

**Parameter Precedence**:
1. Command-line arguments (highest priority)
2. Environment variables from `.env` file
3. Extracted from MODEL_ARN (if available)
4. Default values in code (lowest priority)

For example, if you specify `--region us-west-2` in the command line, it will override any region setting in your `.env` file or defaults.

### Important Notes on Region Configuration

- **Region Compatibility**: The AWS region used for the Bedrock knowledge base must match the region specified in `AWS_REGION` and in the `MODEL_ARN`. Using different regions will result in errors when querying the knowledge base.

### Configuration Precedence

When determining configuration values, the following precedence is used (highest to lowest):

1. Command-line arguments (e.g., `--region`, `--enable-dm`)
2. Environment variables from `.env` file
3. Values extracted from other settings (e.g., region from `MODEL_ARN`)
4. Default values in code

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