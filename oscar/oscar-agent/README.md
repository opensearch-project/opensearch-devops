# OSCAR Agent - Supervisor and Communication Hub

The core Slack integration and AI orchestration system for OSCAR, featuring dual-agent architecture with intelligent routing and comprehensive conversation management.

## Features

- **Dual-Agent Architecture**: Privileged and limited agents with automatic routing
- **Intelligent Authorization**: User-based access control with context propagation
- **Conversation Management**: Persistent context across interactions
- **Slack Integration**: Native Slack events, slash commands, and messaging
- **Async Processing**: Non-blocking event handling with immediate acknowledgment
- **Action Groups**: Extensible function calling for specialized operations

## Architecture

The oscar-agent serves as the central hub with modular components:

### Core Components

- **Supervisor Agent** (`app.py`) - Main Lambda handler and request routing
- **Dual-Agent System** (`bedrock/`) - Privileged and limited Bedrock agents
- **Context Storage** (`context_storage.py`) - DynamoDB-based conversation persistence
- **Configuration** (`config.py`) - Centralized settings with secrets management

### Slack Integration (`slack_handler/`)

**Event Processing:**
- `slack_handler.py` - Main Slack Bolt app integration
- `event_handlers.py` - App mentions and direct message processing
- `message_processor.py` - Query extraction and agent invocation
- `reaction_manager.py` - User feedback through emoji reactions
- `timeout_handler.py` - Request timeout and error handling

**User Interface:**
- `slash_commands.py` - Custom slash commands for operations
- `slack_messaging.py` - Message formatting and delivery
- `message_formatter.py` - Markdown to Slack conversion

### Communication Handler (`communication_handler/`)

**Message Operations:**
- `lambda_handler.py` - Standalone Lambda for message operations
- `message_handler.py` - Cross-channel messaging and automation
- `response_builder.py` - Structured response formatting
- `slack_client.py` - Slack API client wrapper

### AI Integration (`bedrock/`)

**Agent Management:**
- `main_agent.py` - Agent factory and configuration
- `agent_invoker.py` - Bedrock agent invocation and session management
- `query_processor.py` - Query preprocessing and context injection

## Dual-Agent Security Model

### Privileged Agent
- **Access**: Full system capabilities including Jenkins, metrics, messaging
- **Users**: Authorized users in `FULLY_AUTHORIZED_USERS`
- **Functions**: All action groups (Jenkins, metrics, communication)
- **Context**: `[USER_ID: <user_id>]` for audit trails

### Limited Agent
- **Access**: Read-only operations and basic queries
- **Users**: All other users (including unauthorized)
- **Functions**: Information retrieval only
- **Context**: No sensitive operations allowed

## Available Functions

### Jenkins Operations (Privileged Only)
- Job execution with mandatory confirmation
- Job information and parameter discovery
- Connection testing and status checks

### Metrics Analysis (All Users)
- Integration test results and analysis
- Build metrics and component resolution
- Release readiness assessment

### Communication (Privileged Only)
- Cross-channel message sending
- Automated announcements
- Message formatting and delivery

## Slash Commands

| Command | Purpose | Access |
|---------|---------|--------|
| `/oscar-announce` | Send announcements | Privileged |
| `/oscar-assign-owner` | Assign component owners | Privileged |
| `/oscar-request-owner` | Request owner assignment | All |
| `/oscar-rc-details` | Get RC information | All |
| `/oscar-missing-notes` | Find missing release notes | All |
| `/oscar-integration-test` | Test result analysis | All |
| `/oscar-broadcast` | Multi-channel messaging | Privileged |

## Configuration

### Environment Variables
```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...

# Dual-Agent Configuration
OSCAR_PRIVILEGED_BEDROCK_AGENT_ID=...
OSCAR_PRIVILEGED_BEDROCK_AGENT_ALIAS_ID=...
OSCAR_LIMITED_BEDROCK_AGENT_ID=...
OSCAR_LIMITED_BEDROCK_AGENT_ALIAS_ID=...

# Authorization
FULLY_AUTHORIZED_USERS=U091B0QH1QD,W017PN2ADN0
DM_AUTHORIZED_USERS=U091B0QH1QD,W017PN2ADN0
CHANNEL_ALLOW_LIST=#opensearch-release,#opensearch-build

# AWS Configuration
AWS_REGION=us-east-1
CONTEXT_TABLE_NAME=oscar-conversation-context
```

## Conversation Flow

1. **Event Reception**: Slack event received via API Gateway
2. **Async Processing**: Immediate acknowledgment, async processing
3. **User Authorization**: Determine privileged vs limited access
4. **Agent Selection**: Route to appropriate Bedrock agent
5. **Context Injection**: Add conversation history and user context
6. **Agent Invocation**: Execute with proper permissions
7. **Response Processing**: Format and deliver response
8. **Context Storage**: Persist conversation state

## Development

### Adding New Functions
1. Create action group schema in Bedrock console
2. Implement Lambda function for operations
3. Update agent instructions and function mappings
4. Test with appropriate user permissions

### Modifying Authorization
- Update user lists in environment configuration
- Modify routing logic in `message_processor.py`
- Test with both privileged and limited users

The oscar-agent provides secure, scalable Slack integration with intelligent AI routing, ensuring appropriate access control while maintaining conversational context and operational capabilities.