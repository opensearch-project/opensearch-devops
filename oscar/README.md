# OSCAR - OpenSearch Conversational AI Release Assistant

OSCAR is a comprehensive AI-powered assistant system built on AWS Bedrock that helps manage OpenSearch releases, Jenkins operations, and metrics queries through Slack integration.

## 🏗️ Architecture Overview

OSCAR consists of multiple specialized AI agents working together:

- **OSCAR Privileged Agent**: Full access supervisor with advanced capabilities
- **OSCAR Limited Agent**: Restricted access agent for basic operations  
- **Jenkins Agent**: Handles Jenkins CI/CD operations
- **Metrics Agents**: Query OpenSearch metrics (Test, Build, Release)
- **Communication Handler**: Manages Slack integration and routing

## 🚀 Quick Start Deployment

### Prerequisites

Before deploying OSCAR, ensure you have:

1. **AWS CLI configured** with appropriate permissions
2. **CDK installed** (`npm install -g aws-cdk`)
3. **Python 3.12+** with pip
4. **Node.js 18+** for CDK
5. **Pre-existing AWS resources**:
   - VPC with subnets and security groups
   - Knowledge Base in AWS Bedrock
   - Cross-account OpenSearch access role (for metrics)

### Step 1: Configure Environment

1. **Update `cdk/.env`** with your AWS resources:

```bash
# Required Pre-existing Resources
AWS_ACCOUNT_ID=your-account-id
AWS_REGION=us-east-1
VPC_ID=vpc-xxxxxxxxx
SUBNET_IDS=subnet-xxx,subnet-yyy,subnet-zzz
SECURITY_GROUP_ID=sg-xxxxxxxxx
KNOWLEDGE_BASE_ID=your-kb-id
OSCAR_METRICS_LAMBDA_VPC_ROLE_ARN=arn:aws:iam::account:role/role-name

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
CHANNEL_ALLOW_LIST=C1234567890

# Authorization
DM_AUTHORIZED_USERS=U1234567890
FULLY_AUTHORIZED_USERS=U1234567890
```

### Step 2: Deploy Everything

Run the complete deployment script:

```bash
./deploy-complete-oscar.sh
```

This single command will:
1. Deploy all CDK infrastructure stacks
2. Create and configure Bedrock agents
3. Update environment variables dynamically
4. Configure all permissions
5. Verify the deployment

## 📋 What the Complete Deployment Script Does

The `deploy-complete-oscar.sh` script orchestrates the entire OSCAR deployment in the correct order:

### Phase 1: Infrastructure Deployment
- **Permissions Stack**: Creates IAM roles and policies
- **Storage Stack**: Creates DynamoDB tables for context and sessions
- **Lambda Stack**: Deploys all Lambda functions with dependencies
- **API Gateway Stack**: Creates REST API for Slack integration

### Phase 2: Agent Configuration
- **Lambda ARN Updates**: Updates agent configs with deployed Lambda ARNs
- **Agent Deployment**: Creates all Bedrock agents with proper collaborator relationships
- **Resource Capture**: Updates `.env` with all created resource IDs

### Phase 3: Final Configuration
- **Secrets Manager**: Deploys and populates with environment variables
- **Permissions Fixing**: Applies comprehensive IAM and resource-based policies
- **Verification**: Confirms all components are working

## 🔧 Dynamic Resource Management

OSCAR uses a **single source of truth** approach where `cdk/.env` contains all resource configurations:

### Resource Flow
1. **Pre-deployment**: Required resources configured in `.env`
2. **CDK Deployment**: Creates infrastructure, outputs resource IDs
3. **Resource Capture**: `update-cdk-env.sh` captures all created resources
4. **Agent Deployment**: Uses captured Lambda ARNs for action groups
5. **Permissions Update**: `oscar-permissions-fixer.sh` uses dynamic values

### Key Dynamic Resources
- Lambda Function ARNs and Names
- DynamoDB Table Names and ARNs  
- API Gateway URLs and IDs
- IAM Role Names and ARNs
- Secrets Manager Names
- Agent IDs and Aliases

## 📁 Project Structure

```
OSCAR/
├── cdk/                          # CDK Infrastructure
│   ├── .env                      # Main configuration file
│   ├── app.py                    # CDK app entry point
│   ├── stacks/                   # CDK stack definitions
│   ├── lambda/                   # Lambda function source code
│   └── agents/                   # Bedrock agent configurations
├── oscar-agent/                  # Main supervisor agent code
├── jenkins/                      # Jenkins agent code  
├── metrics/                      # Metrics agents code
├── agent-configs/                # Agent configuration files
├── tests/                        # Test files
├── deploy-complete-oscar.sh      # Main deployment script
├── deploy-all-agents.sh          # Agent deployment logic
├── oscar-permissions-fixer.sh    # Comprehensive permissions fixer
├── update-cdk-env.sh            # Resource ID capture script
└── update-lambda-arns.sh        # Lambda ARN update script
```

## 🔐 Security & Permissions

OSCAR implements comprehensive security with multiple layers:

### Identity-Based Policies (IAM Roles)
- **Supervisor Agent**: Bedrock agents, DynamoDB, Lambda invocation
- **Communication Handler**: Bedrock agents, DynamoDB, CloudWatch
- **Metrics Agents**: Cross-account OpenSearch, Secrets Manager
- **Jenkins Agent**: Bedrock agents, CloudWatch

### Resource-Based Policies
- **Lambda Functions**: Allow Bedrock agent invocation
- **Bedrock Agents**: Allow Lambda role access
- **DynamoDB Tables**: Scoped access per agent type

### Authorization Levels
- **Fully Authorized Users**: Complete OSCAR access
- **DM Authorized Users**: Direct message capabilities
- **Channel Allow List**: Restricted channel access

## 🛠️ Key Scripts Explained

### `deploy-complete-oscar.sh`
The master deployment script that orchestrates everything:
- Validates prerequisites
- Deploys infrastructure in dependency order
- Configures agents with proper relationships
- Applies all necessary permissions
- Verifies deployment success

### `oscar-permissions-fixer.sh`
Comprehensive permissions management:
- **Dynamic Configuration**: Reads all values from `.env`
- **Identity-Based Policies**: Updates IAM role policies
- **Resource-Based Policies**: Configures Lambda and Bedrock permissions
- **Cross-Account Access**: Handles OpenSearch metrics permissions

### `update-cdk-env.sh`
Resource capture and propagation:
- Extracts resource IDs from deployed CDK stacks
- Updates `.env` with Lambda ARNs, table names, API Gateway URLs
- Captures agent IDs from deployment files
- Maintains single source of truth

## 🔄 Agent Collaboration System

OSCAR agents work together through a sophisticated collaboration system:

### Supervisor Agents
- **OSCAR Privileged**: Full system access, can invoke all agents
- **OSCAR Limited**: Restricted access, basic operations only

### Specialist Agents  
- **Jenkins Agent**: CI/CD pipeline management
- **Test Metrics Agent**: Integration test results
- **Build Metrics Agent**: Build pipeline metrics
- **Release Metrics Agent**: Release-specific metrics

### Collaboration Flow
1. User sends message to Slack
2. Communication Handler routes to appropriate supervisor
3. Supervisor determines required specialist agents
4. Specialist agents execute specific tasks
5. Results aggregated and returned to user

## 🧪 Testing & Verification

After deployment, verify OSCAR functionality:

### 1. Check Deployed Resources
```bash
# List agents
aws bedrock-agent list-agents --query "agentSummaries[?contains(agentName, 'oscar')]"

# List Lambda functions  
aws lambda list-functions --query "Functions[?contains(FunctionName, 'oscar')]"
```

### 2. Test Slack Integration
- Send a direct message to the OSCAR bot
- Try basic queries like "Hello" or "What can you do?"
- Test metrics queries: "What are the test results for version 3.2.0?"

### 3. Verify Permissions
- Check IAM role policies are applied
- Verify Lambda function resource policies
- Confirm agent collaboration works

## 🚨 Troubleshooting

### Common Issues

**Deployment Fails**
- Check AWS credentials and permissions
- Verify pre-existing resources exist
- Review CloudFormation stack events

**Agent Creation Fails**
- Ensure Lambda functions are deployed first
- Check IAM role permissions
- Verify knowledge base access

**Permissions Issues**
- Run `oscar-permissions-fixer.sh` manually
- Check resource-based policies on Lambda functions
- Verify cross-account role assumptions

**Slack Integration Issues**
- Verify API Gateway URL is correct
- Check Slack app configuration
- Review CloudWatch logs for errors

### Log Locations
- **Lambda Logs**: CloudWatch `/aws/lambda/oscar-*`
- **CDK Deployment**: Local terminal output
- **Agent Deployment**: `deployed-agent-ids.json`

## 🔄 Updates & Maintenance

### Updating Lambda Code
```bash
cd cdk
./prepare_lambda_assets.sh
cdk deploy OscarLambdaStack
```

### Adding New Agents
1. Create agent configuration in `agent-configs/`
2. Add to `deployment-config.json`
3. Run `./deploy-all-agents.sh`
4. Update permissions with `./oscar-permissions-fixer.sh`

### Environment Changes
1. Update `cdk/.env` with new values
2. Run `./update-cdk-env.sh` to propagate changes
3. Redeploy affected stacks as needed

## 📞 Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Review deployment script output
3. Verify all prerequisites are met
4. Check AWS service limits and quotas

## 🎯 Next Steps

After successful deployment:
1. **Test Core Functionality**: Verify all agents respond correctly
2. **Configure Monitoring**: Set up CloudWatch alarms and dashboards  
3. **Train Users**: Provide Slack usage guidelines
4. **Customize Agents**: Adjust agent instructions for your use case
5. **Scale Resources**: Monitor usage and adjust Lambda memory/timeout as needed

OSCAR is now ready to assist with your OpenSearch release management! 🚀