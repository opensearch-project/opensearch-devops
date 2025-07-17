# OSCAR Slack Bot

AI-powered Slack bot with thread-based context and knowledge base integration using Amazon Bedrock.

## Architecture

The OSCAR Slack bot is built using the following components:

- **Slack Bolt Framework**: Handles Slack events and message processing
- **AWS Lambda**: Serverless execution environment
- **DynamoDB**: Session storage for thread context (with TTL)
- **Amazon Bedrock**: Knowledge base queries with context preservation
- **AWS Secrets Manager**: Secure storage for Slack credentials

### Key Components

#### 1. Event Handling
The bot handles two main types of events:
- **Mentions**: When the bot is mentioned in a channel (`@oscar`)
- **Direct Messages** (toggleable via cdk script command line): When users send private messages to the bot

#### 2. Context Management
- **Thread-Based Context**: Messages in the same thread maintain conversation context
- **Session Storage**: Uses DynamoDB to store session IDs and conversation history
- **TTL Mechanism**: Automatically expires old sessions (1 hour) and context (configurable parameter currently set to 7 days)

#### 3. Knowledge Base Integration
- **Amazon Bedrock**: Uses Bedrock's RetrieveAndGenerate API for knowledge base queries
- **Context Enhancement**: Includes previous conversation context in queries
- **Prompt Engineering**: Custom prompt templates for optimal responses

#### 4. Deduplication System
- **Multi-Layer Deduplication**: Prevents duplicate responses to the same message
- **Event Fingerprinting**: Creates unique identifiers for each message
- **Response Tracking**: Checks if the bot has already responded to a message

#### 5. Emoji Reactions
- **Visual Feedback**: Adds emoji reactions to acknowledge messages
- **Processing Indicator**: Uses 👀 (eyes) emoji while processing
- **Completion Status**: Uses ✅ (white_check_mark) for success or ❌ (x) for errors

## Code Structure

The codebase follows a modular design pattern with clear separation of concerns:

### Core Modules

- **app.py**: Main Lambda handler entry point
- **socket_app.py**: Alternative implementation for WebSocket-based deployments
- **oscar/**: Core functionality package
  - **__init__.py**: Package initialization
  - **config.py**: Configuration management
  - **storage.py**: Session and context storage
  - **bedrock.py**: Knowledge base integration
  - **slack_handler.py**: Slack event handling

### Support Files

- **requirements.txt**: Python dependencies
- **deploy.sh**: Deployment script for Serverless Framework
- **.env**: Environment variables (not committed to repository)
- **.env.example**: Example environment variables template
- **serverless.yml**: Serverless Framework configuration

### Tests

- **tests/**: Unit tests for all modules
  - **test_config.py**: Tests for configuration module
  - **test_storage.py**: Tests for storage implementations
  - **test_bedrock.py**: Tests for knowledge base integration
  - **test_slack_handler.py**: Tests for Slack event handling
  - **run_tests.sh**: Script to run all tests with coverage report

## Environment Variables

The following environment variables are required:

```
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
KNOWLEDGE_BASE_ID=your-bedrock-knowledge-base-id
MODEL_ARN=arn:aws:bedrock:region:account:inference-profile/model-id
```

Optional environment variables:

```
AWS_REGION=us-west-2
SLACK_SECRETS_ARN=arn:aws:secretsmanager:region:account:secret:name
SESSIONS_TABLE_NAME=oscar-sessions
CONTEXT_TABLE_NAME=oscar-context
DEDUP_TTL=300
SESSION_TTL=3600
CONTEXT_TTL=172800
MAX_CONTEXT_LENGTH=3000
CONTEXT_SUMMARY_LENGTH=500
PROMPT_TEMPLATE=custom prompt template
```

## Usage Examples

### Channel Mentions

Mention the bot in any channel:
```
@oscar What's the status of OpenSearch 2.11?
```

Reply in thread to maintain context:
```
@oscar What about security issues?
```

### Direct Messages

Send a direct message to the bot:
```
What's new in the latest release?
```

## Development

### Local Testing

To test the bot locally:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Use socket mode for local development:
   ```bash
   python socket_app.py
   ```

### Running Tests

Run the test suite with coverage report:

```bash
cd slack-bot
chmod +x tests/run_tests.sh
./tests/run_tests.sh
```

### Adding Features

When adding new features:

1. Update the appropriate module in the `oscar` package
2. Add tests for the new functionality
3. Test locally using socket mode
4. Update the deployment configuration if necessary
5. Deploy using either CDK or Serverless Framework

### Updating the Lambda Function

To update just the Lambda function code:

```bash
# Create a deployment package with dependencies
mkdir -p lambda_package
cp -r app.py oscar lambda_package/
pip install -r requirements.txt -t lambda_package/
cd lambda_package
zip -r ../lambda_package.zip .
cd ..

# Update the Lambda function
aws lambda update-function-code \
  --function-name oscar-slack-bot \
  --zip-file fileb://lambda_package.zip \
  --region us-west-2

# Clean up
rm -rf lambda_package
rm lambda_package.zip
```

## Troubleshooting

### Common Issues

1. **Bot Not Responding**:
   - Check Lambda function logs in CloudWatch
   - Verify Slack event subscription is properly configured
   - Ensure the bot has been invited to the channel
   - Check Secrets Manager for correct Slack credentials

2. **Knowledge Base Issues**:
   - Verify the KNOWLEDGE_BASE_ID environment variable
   - Check Bedrock permissions in IAM
   - Ensure the knowledge base has been properly indexed

3. **Context Not Working**:
   - Check DynamoDB tables for session and context data
   - Verify TTL settings are correct
   - Ensure you're replying in a thread

4. **Emoji Reactions Not Working**:
   - Verify the bot has the `reactions:write` scope
   - Check Lambda function logs for reaction-related errors

## Design Decisions

### Modular Architecture

The codebase follows a modular design with clear separation of concerns:

- **Configuration**: Centralized in `config.py` with environment variable support
- **Storage**: Abstract interface with multiple implementations (DynamoDB, in-memory)
- **Knowledge Base**: Abstract interface for Bedrock integration with mock implementation for testing
- **Slack Handler**: Encapsulates all Slack-specific logic and event handling

### Interface-Based Design

Abstract base classes are used for key components to enable:

- **Testability**: Mock implementations for unit testing
- **Flexibility**: Easy to swap implementations (e.g., different storage backends)
- **Maintainability**: Clear contracts between components

### Error Handling

Comprehensive error handling strategy:

- **Graceful Degradation**: Fallback mechanisms for API failures
- **Visual Feedback**: Emoji reactions indicate processing status
- **Logging**: Detailed logs for troubleshooting
- **User Communication**: Clear error messages for end users