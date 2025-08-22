# Jenkins Integration for OSCAR

Secure Jenkins job execution through conversational AI with mandatory confirmation workflow and user authorization.

## Features

- **Conversational Interface**: Execute Jenkins jobs through natural language in Slack
- **Security First**: User authorization and mandatory confirmation workflow
- **Job Discovery**: Dynamic job parameter discovery and validation
- **Workflow Monitoring**: Direct links to job execution and progress tracking
- **Audit Trail**: Complete logging of all operations

## Architecture

The Jenkins integration consists of several components:

- **Jenkins Lambda Function** (`oscar-jenkins-agent`) - Core job operations handler
- **Jenkins Agent (Bedrock)** - Conversational interface with confirmation workflow
- **Supervisor Agent** - Request routing and user authorization
- **Message Processor** - User context propagation

## Project Structure

```
jenkins/
├── lambda_function.py          # Main Lambda handler
├── jenkins_client.py           # Jenkins API client
├── job_definitions.py          # Job registry and validation
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── deployment/                 # Deployment scripts and configs
│   ├── update_lambda.sh       # Lambda deployment script
│   └── deploy.sh              # Full deployment script
└── schemas/
    └── jenkins_action_group.json  # Bedrock action group schema
```

## Available Functions

| Function | Purpose | Parameters | Usage |
|----------|---------|------------|-------|
| `get_job_info` | Get job details without execution | `job_name` (optional) | "what params does docker-scan need?" |
| `trigger_job` | Execute Jenkins job | `job_name`, `confirmed`, job params | Requires confirmation workflow |
| `list_jobs` | List available jobs | None | "what jobs are available?" |
| `test_connection` | Jenkins connectivity check | None | "is Jenkins working?" |

## Supported Jobs

### docker-scan
- **Purpose**: Triggers Docker security scan
- **Parameters**: `IMAGE_FULL_NAME` (required)
- **Example**: `IMAGE_FULL_NAME=alpine:3.19`

### Pipeline central-release-promotion
- **Purpose**: Promotes release candidates to final release
- **Parameters**: 
  - `RELEASE_VERSION` (required): Version to promote (e.g., "2.11.0")
  - `OPENSEARCH_RC_BUILD_NUMBER` (required): OpenSearch RC build number
  - `OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER` (required): Dashboards RC build number

## Security Model

### User Authorization
- Uses `AUTHORIZED_MESSAGE_SENDERS` allowlist from environment variables
- All queries include user context: `[USER_ID: <user_id>]`
- Supervisor agent validates permissions before job execution

### Mandatory Confirmation Workflow
1. **Information Phase**: Agent calls `get_job_info` to show job details
2. **Confirmation Phase**: User must explicitly confirm with "yes"
3. **Execution Phase**: Agent calls `trigger_job` with `confirmed=true`

## Usage Examples

### Basic Job Execution
```
User: "Run docker scan on alpine:3.19"
Agent: "Ready to run docker-scan job on alpine:3.19. This will trigger security scan at https://build.ci.opensearch.org/job/docker-scan. Do you want to proceed? (yes/no)"
User: "yes"
Agent: "Success! Job triggered. Workflow URL: https://build.ci.opensearch.org/job/docker-scan/5249/"
```

### Release Promotion
```
User: "Promote version 2.11.0 with OpenSearch RC 123 and Dashboards RC 456"
Agent: [Shows job details and asks for confirmation]
User: "yes"
Agent: [Executes central-release-promotion job]
```

## Configuration

### Environment Variables
```bash
# Jenkins Configuration
JENKINS_URL=https://build.ci.opensearch.org
JENKINS_API_TOKEN=<username:token>

# Authorization
AUTHORIZED_MESSAGE_SENDERS=U091B0QH1QD,W017PN2ADN0,W017VV9TD33

# AWS Configuration
AWS_REGION=us-east-1
JENKINS_LAMBDA_FUNCTION_NAME=oscar-jenkins-agent
```

## Deployment

### Jenkins Lambda Function
```bash
./deployment/update_lambda.sh
```

### Full System Deployment
```bash
./deployment/deploy.sh
```

## Testing

### Direct Lambda Testing
```bash
# Test job info retrieval
aws lambda invoke --function-name oscar-jenkins-agent \
  --payload '{"function":"get_job_info","parameters":[{"name":"job_name","value":"docker-scan"}]}' \
  response.json

# Test job execution (with confirmation)
aws lambda invoke --function-name oscar-jenkins-agent \
  --payload '{"function":"trigger_job","parameters":[{"name":"job_name","value":"docker-scan"},{"name":"IMAGE_FULL_NAME","value":"alpine:3.19"},{"name":"confirmed","value":"true"}]}' \
  response.json
```

### End-to-End Testing
1. Send message in Slack: "Run docker scan on alpine:3.19"
2. Verify agent requests confirmation
3. Reply "yes" and verify job executes with workflow URL

## Troubleshooting

### Common Issues

**"Access denied" errors**
- Check user is in `AUTHORIZED_MESSAGE_SENDERS`
- Verify supervisor agent has user-authentication action group

**"Confirmation parameter" errors**
- Ensure agent follows two-phase workflow (get_job_info → trigger_job)
- Check agent instructions are updated in Bedrock console

**"HTTP 401 Unauthorized" errors**
- Verify `JENKINS_API_TOKEN` format is `username:token`
- Check Jenkins credentials are valid

### Log Monitoring
```bash
# Jenkins Lambda logs
aws logs tail /aws/lambda/oscar-jenkins-agent --follow

# Supervisor Agent logs  
aws logs tail /aws/lambda/oscar-supervisor-agent --follow
```

## Development

### Adding New Jobs
1. Create job class in `job_definitions.py` extending `BaseJobDefinition`
2. Register job in `job_registry`
3. Deploy updated Lambda function

### Modifying Security Rules
- Update `AUTHORIZED_MESSAGE_SENDERS` in environment configuration
- Modify confirmation logic in `lambda_function.py` if needed

The Jenkins integration provides secure, user-friendly Jenkins job execution through conversational AI while maintaining proper authorization and audit trails.