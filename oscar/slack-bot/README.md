# OpenSearch Conversational Automation for Releases (OSCAR) Slack Bot

A Slack bot for OpenSearch release management, powered by AWS Lambda and Amazon Bedrock.

## Architecture

This Slack bot uses API Gateway and a two-phase processing approach to prevent duplicate responses:

1. **Event Reception**: Slack sends events to an API Gateway endpoint, which triggers the Lambda function.

2. **Immediate Acknowledgment**: When a Slack event is received, the Lambda function immediately acknowledges it with a 200 OK response within Slack's 3-second timeout window.

3. **Asynchronous Processing**: After acknowledging the event, the Lambda function invokes itself asynchronously to process the event and generate a response.

## Features

- **Thread-Based Context**: Maintains conversation context within Slack threads
- **Knowledge Base Integration**: Uses Amazon Bedrock to query OpenSearch documentation
- **Emoji Reactions**: Provides visual feedback on message processing status
- **Deduplication**: Prevents duplicate responses to the same message
<!-- - **Throttling**: Rate limits requests to prevent overuse -->
- **Toggleable DM Support**: Enable or disable direct message functionality

## Configuration

The bot uses environment variables set by the CDK deployment. Key variables include:

### Required Environment Variables
| Variable | Description | Source |
|----------|-------------|--------|
| `SLACK_BOT_TOKEN` | Slack bot token | `.env` file |
| `SLACK_SIGNING_SECRET` | Slack signing secret | `.env` file |
| `KNOWLEDGE_BASE_ID` | Bedrock knowledge base ID | `.env` file |
| `AWS_REGION` | AWS region | `.env` file |

### Configuration from CDK Context
Most bot behavior is configured via `cdk/cdk.context.json`:
- **Model**: Claude 3.5 Sonnet (enhanced AI capabilities)
- **Context Limits**: 5000 chars max, 1000 char summaries
- **Timeouts**: 120 second Lambda timeout for complex queries
- **Tables**: DynamoDB table names and TTL settings
- **Features**: Direct message support, CORS origins

### Recent Improvements
- **Enhanced Context Preservation**: Better thread-based conversation continuity
- **Improved AI Model**: Upgraded to Claude 3.5 Sonnet for higher quality responses
- **Optimized Performance**: Better context summarization and query processing
- **Robust Error Handling**: Graceful fallbacks and comprehensive logging

## Deployment

See the main [README.md](../README.md) for deployment instructions.

## Project Structure

```
slack-bot/
├── app.py                # Lambda handler
├── bedrock.py            # Bedrock integration
├── config.py             # Configuration management
├── slack_handler.py      # Slack event handling
├── storage.py            # DynamoDB storage
├── requirements.txt      # Python dependencies with security fixes
├── setup.py              # Package setup with security checks
├── install_deps.sh       # Dependency installation script
└── tests/                # Unit tests
    ├── run_tests.sh      # Test runner script
    └── ...               # Test files
```

## How It Works

1. Slack sends an event to the API Gateway endpoint configured as a webhook URL in Slack
2. API Gateway forwards the event to the Lambda function using the Lambda proxy integration
3. The Lambda function immediately acknowledges the event with a 200 OK response
4. The Lambda function invokes itself asynchronously to process the event
5. The asynchronous Lambda function:
   - Checks if the user is being throttled
   - Processes the event and queries the knowledge base
   - Maintains conversation context in DynamoDB
   - Sends a response to Slack with appropriate emoji reactions

## Troubleshooting

### No Responses

If the bot is not responding:

1. Check the CloudWatch logs for errors
2. Verify that the Lambda function has permission to send messages to Slack
3. Ensure that the bot has been invited to the channel and has the necessary permissions
4. Check that the Slack credentials are correctly set in the environment variables

## Security

### Dependency Security

This project includes security measures to prevent vulnerabilities in dependencies:

1. **Pinned Dependencies**: All dependencies have explicitly pinned versions in requirements.txt
2. **Security Fixes**: urllib3 is pinned to version 2.5.0 to prevent CVE-2025-50181 and CVE-2025-50182
3. **Installation Script**: The `install_deps.sh` script installs dependencies and verifies security

To install dependencies securely:
```bash
chmod +x install_deps.sh
./install_deps.sh
```