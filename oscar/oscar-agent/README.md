# OSCAR Agent

The core application logic for the OSCAR Slack bot, handling AI interactions, message processing, and Slack integration.

## Architecture

The oscar-agent is structured into three main modules:

### communication_handler/
Handles all message processing, formatting, and response building.

**Key Components:**
- `message_handler.py` - Central message processing logic
- `message_formatter.py` - Response formatting and templating
- `response_builder.py` - Constructs structured responses
- `template_processor.py` - Template rendering and customization
- `context_storage.py` - Conversation context management
- `slack_client.py` - Slack API interactions

### slack_handler/
Manages Slack-specific functionality and event processing.

**Key Components:**
- `slack_handler.py` - Main Slack integration logic
- `event_handlers.py` - Processes different Slack event types
- `message_processor.py` - Slack message parsing and validation
- `slash_commands.py` - Custom slash command handling
- `reaction_manager.py` - Emoji reaction processing
- `authorization.py` - Slack app authentication
- `timeout_handler.py` - Request timeout management

### bedrock/
Core AI agent functionality and decision-making logic.

**Key Components:**
- Contains the main AI reasoning and response generation
- Integrates with AWS Bedrock for AI capabilities
- Manages conversation flow and context

## Main Application Files

- `app.py` - Lambda entry point and request routing
- `config.py` - Configuration management and environment variables
- `storage.py` - Data persistence and retrieval logic

## Modularity

The architecture promotes separation of concerns:
- **Communication layer** handles message formatting and delivery
- **Slack layer** manages platform-specific functionality  
- **Agent layer** contains core AI logic
- **Storage layer** abstracts data persistence

This modular design allows for easy testing, maintenance, and potential expansion to other platforms.