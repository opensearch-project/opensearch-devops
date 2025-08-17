# OSCAR Deployment Scripts

This directory contains the main deployment scripts for the OSCAR system. These scripts handle full deployments including infrastructure setup, permissions, and dependencies.

## Scripts Overview

### `deploy_all.sh`
**Complete system deployment** - Deploys everything from scratch:
- CDK infrastructure
- DynamoDB tables setup
- All Lambda functions with proper permissions
- Bedrock agent permissions

Use this for:
- Initial deployment
- Complete system rebuild
- After major infrastructure changes

### `deploy_metrics.sh`
**Metrics Lambda functions deployment** - Deploys all 4 metrics functions:
- oscar-test-metrics-agent-new
- oscar-build-metrics-agent-new  
- oscar-release-metrics-agent-new
- oscar-deployment-metrics-agent-new

Includes:
- IAM role creation/updates
- VPC configuration
- Bedrock agent permissions
- Environment variables setup

### `deploy_communication_handler.sh`
**Communication Handler deployment** - Deploys the communication orchestration function:
- oscar-communication-handler

Includes:
- IAM role with DynamoDB and Bedrock permissions
- Slack SDK dependencies
- Bedrock invoke permissions

### `deploy_oscar_agent.sh`
**Main OSCAR agent deployment** - Deploys the primary Slack bot function:
- oscar-supervisor-agent

Includes:
- Complete dependency installation (Slack SDK, Bolt, OpenSearch)
- IAM role with full permissions
- Environment variables for all features
- Code verification checks

## Key Features

### Proper Dependency Management
- All scripts install dependencies with `--upgrade` flag
- Individual fallback installation for critical packages
- Dependency verification before deployment
- Comprehensive requirements.txt for each component

### Integrated Permissions
- No separate "fix" scripts needed
- IAM roles created with correct permissions from start
- DynamoDB access properly configured
- Bedrock agent permissions included

### Error Handling
- Environment variable validation
- Dependency verification
- Function existence checks
- Proper cleanup on failure

## Usage

### Full Deployment
```bash
# Deploy everything from scratch
./deployment_scripts/deploy_all.sh
```

### Individual Components
```bash
# Deploy only metrics functions
./deployment_scripts/deploy_metrics.sh

# Deploy only communication handler
./deployment_scripts/deploy_communication_handler.sh

# Deploy only main OSCAR agent
./deployment_scripts/deploy_oscar_agent.sh
```

### Code Updates Only
For updating just the code without touching permissions or infrastructure:
```bash
# Update all Lambda function code
./lambda_update_scripts/update_all.sh

# Update individual components
./lambda_update_scripts/update_metrics.sh
./lambda_update_scripts/update_communication_handler.sh
./lambda_update_scripts/update_slack_agent.sh
```

## Prerequisites

1. **Environment Variables**: Ensure `.env` file exists with required variables
2. **AWS CLI**: Configured with appropriate permissions
3. **Python & pip**: For dependency installation
4. **CDK**: For infrastructure deployment (only for `deploy_all.sh`)

## Migration from Old Scripts

The old deployment scripts have been consolidated and improved:

- ❌ `deploy_all.sh` → ✅ `deployment_scripts/deploy_all.sh`
- ❌ `deploy_all_with_dependencies.sh` → ✅ `deployment_scripts/deploy_all.sh`
- ❌ `deploy_metrics.sh` → ✅ `deployment_scripts/deploy_metrics.sh`
- ❌ `deploy_communication_handler.sh` → ✅ `deployment_scripts/deploy_communication_handler.sh`
- ❌ `deploy_oscar_agent.sh` → ✅ `deployment_scripts/deploy_oscar_agent.sh`
- ❌ `fix_*` scripts → ✅ Integrated into main deployment scripts

## DynamoDB Setup

DynamoDB setup scripts have been moved to the CDK directory:
- `cdk/setup_dynamodb_tables.py`
- `cdk/recreate_dynamodb_tables.sh`

These are automatically called by `deploy_all.sh` but can be run independently if needed.