# OSCAR - AI-Powered Slack Bot

OSCAR is a serverless AI assistant built for Slack that leverages AWS Bedrock for intelligent responses and maintains conversation context across interactions.

## Architecture Overview

The system is built with a modular, serverless architecture consisting of:

- **oscar-agent/**: Core bot logic and Slack integration
- **metrics/**: Analytics and performance monitoring
- **deployment_scripts/**: Deployment automation and infrastructure setup

## Key Features

- **Contextual Conversations**: Maintains conversation history and context
- **Intelligent Responses**: Powered by AWS Bedrock AI models
- **Slack Integration**: Native Slack bot with event handling
- **Serverless Architecture**: AWS Lambda-based for scalability
- **Analytics**: Built-in metrics and monitoring

## Project Structure

```
OSCAR/
├── oscar-agent/              # Main bot application
│   ├── communication_handler/    # Message processing and formatting
│   ├── slack_handler/           # Slack-specific event handling
│   └── bedrock/                # Core AI agent logic
├── metrics/                 # Analytics and monitoring
├── deployment_scripts/      # Full deployment automation
│   ├── deploy_all.sh           # Complete system deployment
│   ├── deploy_metrics.sh       # Metrics functions deployment
│   ├── deploy_communication_handler.sh  # Communication handler deployment
│   └── deploy_oscar_agent.sh   # Main agent deployment
└── lambda_update_scripts/   # Code-only updates (preserves permissions)
    ├── update_all.sh           # Update all Lambda function code
    ├── update_metrics.sh       # Update metrics code only
    ├── update_communication_handler.sh  # Update communication handler code
    └── update_slack_agent.sh   # Update main agent code only
```

## Getting Started

### Full Deployment (New Setup)
```bash
# 1. Configure environment variables
cp .env.example .env
# Edit .env with your values

# 2. Deploy complete system
./deployment_scripts/deploy_all.sh
```

### Code Updates (Existing Deployment)
```bash
# Update all Lambda function code (preserves permissions)
./lambda_update_scripts/update_all.sh

# Or update individual components
./lambda_update_scripts/update_metrics.sh
./lambda_update_scripts/update_communication_handler.sh
./lambda_update_scripts/update_slack_agent.sh
```

### Individual Component Deployment
```bash
# Deploy specific components with full setup
./deployment_scripts/deploy_metrics.sh
./deployment_scripts/deploy_communication_handler.sh
./deployment_scripts/deploy_oscar_agent.sh
```

## Deployment Scripts Overview

- **deployment_scripts/**: Full deployment with infrastructure, permissions, and dependencies
- **lambda_update_scripts/**: Code-only updates that preserve existing configurations

Each directory has its own README with detailed information about structure and functionality.