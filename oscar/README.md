# OSCAR - AI-Powered Operations Assistant

OSCAR is a serverless AI assistant that brings intelligent automation to Slack workspaces. Built on AWS Bedrock and Lambda, it provides conversational interfaces for complex operations like Jenkins job management, system monitoring, and team collaboration.

## Features

### Conversational AI
- **Natural Language Processing**: Understand complex requests in plain English
- **Context Awareness**: Maintains conversation history and context across interactions
- **Multi-Agent Architecture**: Specialized agents for different domains (Jenkins, monitoring, etc.)

### Operations Automation
- **Jenkins Integration**: Secure job execution with mandatory confirmation workflows
- **System Monitoring**: Real-time metrics and performance tracking
- **User Authorization**: Role-based access control with audit trails

### Developer Experience
- **Slack Native**: Seamless integration with existing Slack workflows
- **Serverless Architecture**: Auto-scaling AWS Lambda functions
- **Infrastructure as Code**: CDK-based deployment and management

## Use Cases

- **DevOps Teams**: Execute Jenkins jobs, monitor deployments, manage releases
- **Engineering Teams**: Automate routine tasks, get system status, troubleshoot issues
- **Operations Teams**: Monitor metrics, manage infrastructure, coordinate responses

## Architecture

OSCAR uses a modular, event-driven architecture:

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│    Slack    │───▶│   Gateway    │───▶│  Supervisor     │
│   Events    │    │   Lambda     │    │    Agent        │
└─────────────┘    └──────────────┘    └─────────────────┘
                                                │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             │                             │
            ┌──────▼──────┐              ┌──────▼──────┐              ┌──────▼──────┐
            │   Jenkins   │              │  Monitoring │              │   Future    │
            │  Specialist │              │  Specialist │              │ Specialists │
            └─────────────┘              └─────────────┘              └─────────────┘
```

## Project Structure

```
OSCAR/
├── oscar-agent/              # Core AI agent and Slack integration
│   ├── app.py                   # Main supervisor agent
│   ├── slack_handler/           # Slack event processing
│   ├── communication_handler/   # Message formatting and routing
│   └── bedrock/                # AI agent orchestration
├── jenkins/                  # Jenkins operations integration
│   ├── lambda_function.py       # Jenkins job execution
│   ├── jenkins_client.py        # Jenkins API client
│   └── job_definitions.py       # Job registry and validation
├── metrics/                  # Analytics and monitoring
│   ├── lambda_function.py       # Metrics collection
│   └── storage.py              # Data persistence
├── cdk/                      # Infrastructure as Code
│   ├── stacks/                  # CDK stack definitions
│   └── lambda/                  # Lambda function configurations
├── tests/                    # Comprehensive test suite
├── deployment_scripts/       # Full deployment automation
└── lambda_update_scripts/    # Code-only updates
```

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.12+
- Slack app with bot token and signing secret

### Initial Setup
```bash
# 1. Clone and configure
git clone <repository>
cd OSCAR
cp .env.example .env
# Edit .env with your AWS and Slack credentials

# 2. Deploy infrastructure
./deployment_scripts/deploy_all.sh

# 3. Configure Slack app
# - Set Request URL to your API Gateway endpoint
# - Subscribe to bot events (message.channels, app_mention)
# - Install app to workspace
```

### Development Workflow
```bash
# Update code without changing infrastructure
./lambda_update_scripts/update_all.sh

# Deploy specific components
./lambda_update_scripts/update_slack_agent.sh
./lambda_update_scripts/update_jenkins.sh
./lambda_update_scripts/update_metrics.sh
```

## Key Components

### Supervisor Agent
- Routes requests to specialized agents
- Handles user authorization and context
- Manages conversation flow and error handling

### Jenkins Integration
- Secure job execution with confirmation workflows
- Dynamic job discovery and parameter validation
- Real-time progress monitoring with workflow URLs

### Metrics System
- Performance tracking and analytics
- Usage patterns and error monitoring
- Custom dashboards and alerting

### Infrastructure
- CDK-based AWS resource management
- DynamoDB for conversation storage
- Lambda functions with proper IAM roles

## Security

- **User Authorization**: Allowlist-based access control
- **Confirmation Workflows**: Mandatory approval for sensitive operations
- **Audit Trails**: Complete logging of all operations
- **Secrets Management**: AWS Secrets Manager integration
- **Least Privilege**: Minimal IAM permissions per component

## Testing

```bash
# Run comprehensive test suite
cd tests
./run_tests.sh

# Test specific components
python -m pytest test_slack_handler.py
python -m pytest test_jenkins.py
python -m pytest test_metrics.py
```

## Monitoring

- **CloudWatch Logs**: Centralized logging for all components
- **Metrics Dashboard**: Real-time performance monitoring
- **Error Tracking**: Automated alerting for failures
- **Usage Analytics**: User interaction patterns and trends

## Contributing

1. **Development**: Use `lambda_update_scripts/` for rapid iteration
2. **Testing**: Run full test suite before deployment
3. **Documentation**: Update relevant READMEs for changes
4. **Security**: Follow principle of least privilege

## Deployment Options

### Full Deployment (New Environment)
- Complete infrastructure setup
- All permissions and dependencies
- Use `deployment_scripts/deploy_all.sh`

### Code Updates (Existing Environment)
- Preserves existing configurations
- Faster deployment for development
- Use `lambda_update_scripts/update_all.sh`

### Infrastructure Changes
- Use CDK for infrastructure modifications
- Deploy through `cdk/` directory
- Includes DynamoDB, IAM roles, API Gateway

OSCAR transforms complex operations into simple conversations, making powerful automation accessible to every team member.