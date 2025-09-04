# OSCAR CDK Infrastructure

This directory contains the AWS CDK infrastructure code for OSCAR (OpenSearch Conversational AI Release Assistant).

## 🏗️ Infrastructure Components

The CDK deploys:
- **Lambda Functions**: All OSCAR agent implementations
- **DynamoDB Tables**: Session and context management
- **IAM Roles & Policies**: Security and permissions
- **API Gateway**: Slack integration endpoint
- **Secrets Manager**: Centralized configuration

## 📋 CDK Stacks

| Stack | Purpose | Resources |
|-------|---------|-----------|
| `OscarPermissionsStack` | IAM roles and policies | Execution roles for Lambda and Bedrock |
| `OscarStorageStack` | Data persistence | DynamoDB tables for sessions/context |
| `OscarLambdaStack` | Compute functions | All Lambda functions with VPC config |
| `OscarApiGatewayStack` | Slack integration | REST API with Lambda integration |
| `OscarSecretsStack` | Configuration management | Secrets Manager for env variables |

## 🚀 Deployment

**Use the main deployment script** (recommended):
```bash
# From project root
./deploy-complete-oscar.sh
```

**Manual CDK deployment** (advanced):
```bash
cd cdk
pip install -r requirements.txt
cdk deploy --all --require-approval never
```

## ⚙️ Configuration

### Required Environment Variables (`.env`)
```bash
# AWS Configuration
AWS_ACCOUNT_ID=your-account-id
AWS_REGION=us-east-1

# Pre-existing Resources (REQUIRED)
VPC_ID=vpc-xxxxxxxxx
SUBNET_IDS=subnet-xxx,subnet-yyy
SECURITY_GROUP_ID=sg-xxxxxxxxx
KNOWLEDGE_BASE_ID=your-kb-id
OSCAR_METRICS_LAMBDA_VPC_ROLE_ARN=arn:aws:iam::account:role/role-name

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
```

### Dynamic Resources (Auto-populated)
These are automatically captured during deployment:
- Lambda function ARNs
- DynamoDB table names
- API Gateway URLs
- IAM role ARNs
- Agent IDs and aliases

## 🔧 Key Files

| File | Purpose |
|------|---------|
| `app.py` | CDK application entry point |
| `.env` | Configuration and resource IDs |
| `prepare_lambda_assets.sh` | Packages Lambda code with dependencies |
| `stacks/` | CDK stack definitions |
| `lambda/` | Lambda function source code |
| `agents/` | Bedrock agent configurations |

## 🛠️ Development Workflow

1. **Modify Infrastructure**: Update stack files in `stacks/`
2. **Test Changes**: `cdk diff StackName`
3. **Deploy Changes**: `cdk deploy StackName`
4. **Update Permissions**: Run `../oscar-permissions-fixer.sh`

## 📊 Lambda Functions Deployed

| Function | Purpose | VPC | Memory | Timeout |
|----------|---------|-----|--------|---------|
| `oscar-supervisor-agent-cdk` | Main OSCAR logic | No | 1024MB | 180s |
| `oscar-communication-handler-cdk` | Slack integration | No | 512MB | 180s |
| `oscar-jenkins-agent-cdk` | Jenkins operations | No | 512MB | 180s |
| `oscar-*-metrics-agent-cdk` | Metrics queries | Yes | 512MB | 180s |

## 🔐 Security Features

- **Least Privilege**: Each Lambda has minimal required permissions
- **VPC Isolation**: Metrics functions run in VPC for OpenSearch access
- **Resource-Based Policies**: Lambda functions secured for Bedrock access
- **Cross-Account Access**: Secure OpenSearch metrics access

## 🧹 Cleanup

**Remove all resources**:
```bash
cdk destroy --all
```

**Note**: Some resources like S3 buckets may need manual cleanup if they contain data.

## 📞 Troubleshooting

**Common Issues**:
- **Bootstrap Required**: Run `cdk bootstrap` if first deployment
- **Permission Errors**: Ensure AWS credentials have CDK permissions
- **VPC Resources**: Verify VPC, subnets, and security groups exist
- **Lambda Packaging**: Run `prepare_lambda_assets.sh` if Lambda deployment fails

**Useful Commands**:
```bash
cdk ls                    # List all stacks
cdk diff                  # Show changes
cdk synth                 # Generate CloudFormation
cdk doctor                # Check CDK setup
```