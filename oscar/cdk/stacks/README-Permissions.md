# OSCAR Permissions Stack

The OSCAR Permissions Stack (`OscarPermissionsStack`) provides comprehensive IAM roles and policies for all OSCAR infrastructure components with least-privilege access and proper security boundaries.

## Overview

This stack creates IAM roles and policies for:

- **Bedrock Agents**: Execution role with permissions for Lambda invocation, Knowledge Base access, and model invocation
- **Lambda Functions**: Multiple execution roles for different function types (base, VPC, communication handler, Jenkins)
- **API Gateway**: Execution role with Lambda invocation and CloudWatch logging permissions
- **Cross-Account Access**: Secure cross-account role assumption for OpenSearch metrics access

## Features

### Least-Privilege Security

- **Resource-Specific Permissions**: All policies use specific resource ARNs instead of wildcards where possible
- **Conditional Access**: Policies include conditions for enhanced security (e.g., source account validation)
- **Attribute-Level Controls**: DynamoDB policies include attribute-level access controls
- **Service-Specific Roles**: Separate roles for different services with tailored permissions

### Policy Validation

The stack includes a comprehensive policy validation system (`PolicyValidator`) that checks for:

- Overly broad actions (wildcards, dangerous permissions)
- Missing resource constraints on sensitive actions
- Missing conditions where they should be present
- Proper effect usage and security best practices

### Modular Design

- **Centralized Policy Definitions**: All policies are defined in `policy_definitions.py` for easy maintenance
- **Reusable Components**: Policies can be reused across different roles and stacks
- **Extensible Architecture**: Easy to add new roles and policies as needed

## Usage

### Basic Usage

```python
from aws_cdk import App, Stack
from stacks.permissions_stack import OscarPermissionsStack

app = App()
stack = Stack(app, "MyStack")

# Create permissions stack
permissions = OscarPermissionsStack(stack, "OscarPermissions")

# Use the roles in other resources
bedrock_agent_role = permissions.bedrock_agent_role
lambda_roles = permissions.lambda_execution_roles
api_gateway_role = permissions.api_gateway_role
```

### Role Types

#### Bedrock Agent Role
- **Purpose**: Execution role for Bedrock agents
- **Permissions**: Lambda invocation, Knowledge Base access, model invocation
- **Trust Policy**: Bedrock service with source account conditions

#### Lambda Execution Roles

1. **Base Role** (`lambda_execution_roles["base"]`)
   - Standard Lambda functions
   - DynamoDB access, Secrets Manager access, Bedrock agent invocation

2. **VPC Role** (`lambda_execution_roles["vpc"]`)
   - VPC-deployed Lambda functions (metrics agents)
   - Cross-account OpenSearch access, VPC execution permissions

3. **Communication Handler Role** (`lambda_execution_roles["communication"]`)
   - Communication handler Lambda function
   - Message routing, context storage, Slack integration

4. **Jenkins Role** (`lambda_execution_roles["jenkins"]`)
   - Jenkins integration Lambda function
   - Jenkins API access, job monitoring

#### API Gateway Role
- **Purpose**: API Gateway execution role
- **Permissions**: Lambda invocation, CloudWatch logging
- **Use Case**: Slack webhook endpoints

## Security Features

### Resource Constraints

All policies use specific resource ARNs:

```python
# Example: DynamoDB access is restricted to OSCAR tables
"Resource": [
    "arn:aws:dynamodb:us-east-1:123456789012:table/oscar-sessions*",
    "arn:aws:dynamodb:us-east-1:123456789012:table/oscar-context*"
]
```

### Conditional Access

Policies include conditions for enhanced security:

```python
# Example: Cross-account access with external ID
"Condition": {
    "StringEquals": {
        "sts:ExternalId": "oscar-metrics-access"
    }
}
```

### Attribute-Level Controls

DynamoDB policies include attribute-level access:

```python
"Condition": {
    "ForAllValues:StringEquals": {
        "dynamodb:Attributes": ["event_id", "ttl", "session_data"]
    }
}
```

## Policy Validation

The stack includes comprehensive policy validation:

```python
from utils.policy_validator import PolicyValidator

validator = PolicyValidator()
issues = validator.validate_policy_statement(policy_statement)
report = validator.generate_validation_report(validation_results)
```

### Validation Checks

- **Broad Actions**: Detects overly permissive actions like `*` or `service:*`
- **Resource Constraints**: Ensures sensitive actions have specific resource ARNs
- **Missing Conditions**: Identifies where conditions should be added for security
- **Cross-Account Access**: Validates proper restrictions on `sts:AssumeRole`

## Environment Variables

Required environment variables:

- `CDK_DEFAULT_ACCOUNT`: AWS account ID
- `CDK_DEFAULT_REGION`: AWS region (default: us-east-1)

## Outputs

The stack provides CloudFormation outputs for all created roles:

- `BedrockAgentRoleArn`: Bedrock agent execution role ARN
- `LambdaExecutionRole{Type}Arn`: Lambda execution role ARNs by type
- `ApiGatewayRoleArn`: API Gateway execution role ARN

## Testing

Run the test suite to validate the permissions stack:

```bash
cd cdk
python -m pytest tests/test_permissions_stack.py -v
```

### Test Coverage

- Role creation and configuration
- Policy attachment and validation
- Least-privilege compliance
- Cross-account access restrictions
- Secrets Manager access controls
- Output generation

## Security Recommendations

### For Bedrock Agents
- Use specific Lambda function ARNs instead of wildcards
- Restrict model access to only required foundation models
- Add source account conditions to trust policy
- Use specific Knowledge Base ARNs when possible

### For Lambda Functions
- Use DynamoDB attribute-level conditions
- Restrict Secrets Manager access to specific secret ARNs
- Add VPC endpoint policies for enhanced security
- Use resource-based policies where appropriate

### For API Gateway
- Use resource-based policies for additional security
- Implement request validation and rate limiting
- Add CloudWatch logging for audit trails
- Use API keys and request signing where appropriate

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed and environment variables are set
2. **Policy Validation Failures**: Check policy definitions for overly broad permissions
3. **Cross-Account Access Issues**: Verify external account role exists and trust policy is correct
4. **Resource ARN Mismatches**: Ensure account ID and region are correctly set in environment variables

### Debug Mode

Enable debug logging for detailed policy analysis:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding new roles or policies:

1. Add policy definitions to `policy_definitions.py`
2. Update the permissions stack to use the new policies
3. Add corresponding tests in `test_permissions_stack.py`
4. Run policy validation to ensure compliance
5. Update this documentation

## Related Files

- `permissions_stack.py`: Main permissions stack implementation
- `policy_definitions.py`: Centralized policy definitions with least-privilege principles
- `policy_validator.py`: Policy validation utilities
- `test_permissions_stack.py`: Comprehensive test suite
- `examples/permissions_example.py`: Usage examples