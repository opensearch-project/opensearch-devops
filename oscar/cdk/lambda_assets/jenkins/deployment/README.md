# Jenkins Lambda Deployment Guide

This directory contains scripts for deploying and updating the Jenkins Lambda function.

## Scripts Overview

### 1. `deploy.sh` - Full Deployment
Complete deployment script that creates IAM roles, Lambda function, and all necessary resources.

```bash
./deployment/deploy.sh
```

**Use when:**
- First-time deployment
- Complete infrastructure recreation needed
- IAM roles or permissions need to be updated

**What it does:**
- Creates IAM role with necessary permissions
- Installs dependencies and packages code
- Creates Lambda function with full configuration
- Sets up Secrets Manager access

### 2. `update_lambda.sh` - Code-Only Update
Lightweight update script that only updates the Lambda function code.

```bash
./deployment/update_lambda.sh
```

**Use when:**
- Only Python code has changed
- Want to preserve existing permissions and configuration
- Quick updates during development

**What it does:**
- Packages current code and dependencies
- Updates Lambda function code only
- Preserves existing IAM roles and permissions
- Much faster than full deployment

### 3. `update_config.sh` - Configuration Update
Updates Lambda function configuration (environment variables, timeout, memory).

```bash
./deployment/update_config.sh
```

**Use when:**
- Need to change environment variables
- Adjust timeout or memory settings
- Update configuration without touching code

**What it does:**
- Updates Lambda function configuration
- Preserves code and IAM permissions
- Updates environment variables, timeout, memory

## Configuration Approach

The Jenkins integration now uses a centralized configuration approach:

### Environment Variables Loading
1. **Secrets Manager**: The entire `.env` file is stored in AWS Secrets Manager (`oscar-central-env`)
2. **Config Loading**: `config.py` loads the `.env` from Secrets Manager on initialization
3. **Variable Access**: All configuration variables are available through the `config` object

### Key Configuration Variables
```python
# Jenkins Configuration
JENKINS_URL=https://build.ci.opensearch.org
JENKINS_API_TOKEN=username:token_here
JENKINS_AGENT_ID=your_agent_id
JENKINS_AGENT_ALIAS_ID=your_agent_alias_id
JENKINS_LAMBDA_FUNCTION_NAME=oscar-jenkins-agent

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=395380602281

# Lambda Configuration
LAMBDA_TIMEOUT=180
LAMBDA_MEMORY_SIZE=512
JENKINS_REQUEST_TIMEOUT=30
JENKINS_MAX_RETRIES=3
LOG_LEVEL=INFO
```

## Testing

### Test Configuration
```bash
python test_config.py
```

This will:
- Verify all configuration variables are loaded
- Test Jenkins client initialization
- Test connection to Jenkins server

### Test Deployment
```bash
python deployment/test_deployment.py
```

## Deployment Workflow

### Initial Setup
1. Ensure `.env` file is uploaded to AWS Secrets Manager as `oscar-central-env`
2. Run full deployment: `./deployment/deploy.sh`
3. Test deployment: `python deployment/test_deployment.py`

### Development Updates
1. Make code changes
2. Run code update: `./deployment/update_lambda.sh`
3. Test changes: `python test_config.py`

### Configuration Changes
1. Update `.env` in Secrets Manager
2. Optionally run: `./deployment/update_config.sh` (if Lambda env vars need updating)
3. Test changes: `python test_config.py`

## Troubleshooting

### Common Issues

1. **Secrets Manager Access Denied**
   - Ensure IAM role has `secretsmanager:GetSecretValue` permission
   - Verify secret ARN in IAM policy matches actual secret

2. **Jenkins Connection Failed**
   - Check `JENKINS_URL` in configuration
   - Verify `JENKINS_API_TOKEN` format is `username:token`
   - Test network connectivity from Lambda VPC (if applicable)

3. **Import Errors**
   - Ensure all dependencies are in `requirements.txt`
   - Run code update to refresh dependencies

4. **Configuration Not Loading**
   - Verify `.env` content in Secrets Manager
   - Check CloudWatch logs for configuration loading errors

### Debugging

1. **Check CloudWatch Logs**
   ```bash
   aws logs tail /aws/lambda/oscar-jenkins-agent --follow
   ```

2. **Test Configuration Locally**
   ```bash
   python test_config.py
   ```

3. **Verify Secrets Manager Content**
   ```bash
   aws secretsmanager get-secret-value --secret-id oscar-central-env --query SecretString --output text
   ```

## Security Notes

- Jenkins API tokens are stored securely in AWS Secrets Manager
- IAM roles follow least-privilege principle
- Secrets are loaded at runtime, not stored in Lambda environment variables
- All sensitive data is encrypted at rest and in transit

## Performance Considerations

- **Code Updates**: ~30 seconds (vs ~2-3 minutes for full deployment)
- **Configuration Loading**: Cached after first load per Lambda container
- **Secrets Manager**: Minimal latency impact, called once per container lifecycle