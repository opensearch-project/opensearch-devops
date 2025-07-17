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

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SLACK_BOT_TOKEN` | Slack bot token | Yes | - |
| `SLACK_SIGNING_SECRET` | Slack signing secret | Yes | - |
| `KNOWLEDGE_BASE_ID` | Bedrock knowledge base ID | Yes | - |
| `MODEL_ARN` | Bedrock model ARN | No | Claude 3.5 Haiku |
| `AWS_REGION` | AWS region | No | us-east-1 |
| `SESSIONS_TABLE_NAME` | DynamoDB sessions table name | No | oscar-sessions-v2 |
| `CONTEXT_TABLE_NAME` | DynamoDB context table name | No | oscar-context |
| `DEDUP_TTL` | Deduplication TTL in seconds | No | 300 (5 minutes) |
| `SESSION_TTL` | Session TTL in seconds | No | 3600 (1 hour) |
| `CONTEXT_TTL` | Context TTL in seconds | No | 604800 (7 days) |
| `MAX_CONTEXT_LENGTH` | Maximum context length | No | 3000 |
| `CONTEXT_SUMMARY_LENGTH` | Context summary length | No | 500 |
| `ENABLE_DM` | Enable direct messages | No | false |
| `PROMPT_TEMPLATE` | Custom prompt template | No | Default template |
<!-- | `THROTTLE_REQUESTS_PER_MINUTE` | Maximum requests per minute per user | No | 5 |
| `THROTTLE_WINDOW_SECONDS` | Throttling window in seconds | No | 60 | -->

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
├── requirements.txt      # Python dependencies
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