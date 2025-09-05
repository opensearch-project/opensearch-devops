# OSCAR VPC Stack

The `OscarVpcStack` provides VPC and networking infrastructure for the OSCAR Slack Bot system. This stack imports existing VPC resources and configures security groups, VPC endpoints, and network ACLs for secure Lambda function deployment.

## Features

### VPC Import
- Imports existing VPC (`vpc-0f2061a1321c2d669` by default)
- Supports fallback to default VPC if specific VPC not found
- Configurable via `VPC_ID` environment variable

### Security Groups
- Creates Lambda security group with OpenSearch access
- Configures outbound rules for HTTPS, HTTP, DNS, and OpenSearch
- Supports importing existing security groups via `LAMBDA_SECURITY_GROUP_ID`

### VPC Endpoints
- **Gateway Endpoints** (no additional charges):
  - S3 Gateway Endpoint
  - DynamoDB Gateway Endpoint
- **Interface Endpoints**:
  - Secrets Manager Interface Endpoint
  - STS Interface Endpoint
- Improves security and performance by keeping traffic within AWS network

### Network ACLs
- Custom Network ACLs for Lambda subnets
- Restrictive rules for enhanced security
- Allows outbound HTTPS, HTTP, DNS, and OpenSearch traffic
- Allows inbound ephemeral ports for responses

## Usage

### Basic Usage
```python
from aws_cdk import App, Environment
from stacks.vpc_stack import OscarVpcStack

app = App()
vpc_stack = OscarVpcStack(
    app, 
    "OscarVpcStack",
    env=Environment(
        account="123456789012",
        region="us-east-1"
    )
)
```

### Integration with Lambda Functions
```python
# Get VPC configuration for Lambda deployment
vpc_config = vpc_stack.vpc_config_for_lambda

# Use in Lambda function
lambda_function = lambda_.Function(
    self, "MyFunction",
    # ... other properties
    vpc=vpc_config["vpc"],
    vpc_subnets=ec2.SubnetSelection(subnets=vpc_config["subnets"]),
    security_groups=vpc_config["security_groups"]
)
```

### Subnet Access
```python
# Get private subnet IDs
private_subnets = vpc_stack.get_subnet_ids("private")

# Get public subnet IDs
public_subnets = vpc_stack.get_subnet_ids("public")

# Get isolated subnet IDs
isolated_subnets = vpc_stack.get_subnet_ids("isolated")
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VPC_ID` | Existing VPC ID to import | `vpc-0f2061a1321c2d669` |
| `LAMBDA_SECURITY_GROUP_ID` | Existing security group ID to import | None (creates new) |
| `ENVIRONMENT` | Environment name for tagging | `dev` |

## Outputs

The stack provides the following CloudFormation outputs:

| Output | Description | Export Name |
|--------|-------------|-------------|
| `VpcId` | ID of the imported VPC | `OscarVpcId` |
| `LambdaSecurityGroupId` | Security group ID for Lambda functions | `OscarLambdaSecurityGroupId` |
| `PrivateSubnetIds` | Comma-separated list of private subnet IDs | `OscarPrivateSubnetIds` |
| `VpcCidr` | CIDR block of the VPC | `OscarVpcCidr` |
| `AvailabilityZones` | Availability zones of the VPC | `OscarAvailabilityZones` |

## Security Configuration

### Security Group Rules
The Lambda security group includes the following outbound rules:
- HTTPS (443) to any IPv4 for AWS services and OpenSearch
- HTTP (80) to any IPv4 for external APIs
- DNS (53 UDP/TCP) to any IPv4 for name resolution
- OpenSearch (9200) to any IPv4 for OpenSearch access
- HTTPS (443) within VPC CIDR for VPC endpoint access

### Network ACLs
Custom Network ACLs are applied to Lambda subnets with:
- **Outbound**: HTTPS (443), HTTP (80), DNS (53), OpenSearch (9200)
- **Inbound**: Ephemeral ports (1024-65535) for responses

### VPC Endpoints
VPC endpoints reduce internet traffic and improve security:
- **S3 Gateway**: For S3 access without internet routing
- **DynamoDB Gateway**: For DynamoDB access without internet routing
- **Secrets Manager Interface**: For secure secrets access
- **STS Interface**: For assume role operations

## Testing

### Unit Tests
```bash
cd cdk
python scripts/test_vpc_stack.py
```

### Integration Tests
```bash
cd cdk
python scripts/validate_vpc_integration.py
```

## Dependencies

This stack has no dependencies on other OSCAR stacks and can be deployed independently. Other stacks that depend on VPC resources should reference this stack's outputs.

## Deployment Order

The VPC stack should be deployed early in the deployment sequence, typically after IAM roles but before Lambda functions and other compute resources.

Recommended order:
1. Permissions Stack (IAM roles)
2. **VPC Stack** ← This stack
3. Secrets Stack
4. Storage Stack
5. Lambda Stack
6. Bedrock Agents Stack

## Troubleshooting

### VPC Not Found
If the specified VPC ID is not found:
1. Verify the VPC ID exists in the target region
2. Check AWS credentials have permission to describe VPCs
3. The stack will fall back to the default VPC

### Security Group Import Fails
If importing an existing security group fails:
1. Verify the security group ID exists
2. Check the security group is in the same VPC
3. The stack will create a new security group

### VPC Endpoint Creation Fails
VPC endpoint creation may fail if:
1. The service is not available in the region
2. Subnet configuration is incompatible
3. The stack logs warnings but continues deployment

## Cost Considerations

- **Gateway Endpoints**: No additional charges (S3, DynamoDB)
- **Interface Endpoints**: Charged per endpoint per hour plus data processing
- **Network ACLs**: No additional charges
- **Security Groups**: No additional charges

Interface endpoints typically cost ~$7-10 per endpoint per month but can reduce data transfer costs and improve security.