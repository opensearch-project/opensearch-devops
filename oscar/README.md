# OSCAR - AI-Powered Slack Bot

OSCAR is a serverless AI assistant built for Slack that leverages AWS Bedrock for intelligent responses and maintains conversation context across interactions.

## Architecture Overview

The system is built with a modular, serverless architecture consisting of:

- **oscar-agent/**: Core bot logic and Slack integration
- **metrics/**: Analytics and performance monitoring
- **cdk/**: AWS infrastructure deployment

## Key Features

- **Contextual Conversations**: Maintains conversation history and context
- **Intelligent Responses**: Powered by AWS Bedrock AI models
- **Slack Integration**: Native Slack bot with event handling
- **Serverless Architecture**: AWS Lambda-based for scalability
- **Analytics**: Built-in metrics and monitoring

## Project Structure

```
OSCAR/
├── oscar-agent/           # Main bot application
│   ├── communication_handler/  # Message processing and formatting
│   ├── slack_handler/          # Slack-specific event handling
│   └── bedrock/               # Core AI agent logic
├── metrics/              # Analytics and monitoring
├── cdk/                  # AWS infrastructure code
└── deployment_scripts/   # Deployment automation
```

## Getting Started

1. Configure your environment variables in `.env`
2. Run deployment scripts to set up AWS infrastructure
3. Configure your Slack app with the generated webhook URL
4. Deploy the bot code to AWS Lambda

Each major component has its own README with detailed information about structure and functionality.