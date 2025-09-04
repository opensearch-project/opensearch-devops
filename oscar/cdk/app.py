#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
"""
Main CDK application for OSCAR infrastructure.

This module defines the main CDK application that deploys the complete OSCAR infrastructure
including permissions, secrets, storage, VPC, API Gateway, Knowledge Base, Lambda functions,
and Bedrock agents.
"""

import logging
import os
from typing import Optional
from aws_cdk import (
    App,
    Environment,
    Tags
)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not available, manually load .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Import working stacks
from stacks.permissions_stack import OscarPermissionsStack
from stacks.secrets_stack import OscarSecretsStack
from stacks.storage_stack import OscarStorageStack
from stacks.vpc_stack import OscarVpcStack
from stacks.api_gateway_stack import OscarApiGatewayStack
from stacks.knowledge_base_stack import OscarKnowledgeBaseStack
from stacks.lambda_stack import OscarLambdaStack
from stacks.bedrock_agents_stack import OscarAgentsStack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Deploy the complete OSCAR infrastructure.
    
    This function initializes the CDK app, creates all required stacks in dependency order,
    and synthesizes the CloudFormation templates.
    """
    app = App()

    # Get account and region from environment variables
    account: Optional[str] = os.environ.get("CDK_DEFAULT_ACCOUNT")
    region: Optional[str] = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
    environment: str = os.environ.get("ENVIRONMENT", "dev")

    if not account:
        raise ValueError("CDK_DEFAULT_ACCOUNT environment variable must be set")

    logger.info(f"Deploying to account: {account}")
    logger.info(f"Deploying to region: {region}")
    logger.info(f"Environment: {environment}")

    env = Environment(account=account, region=region)

    # Deploy stacks in dependency order
    
    # 1. Permissions (IAM roles and policies)
    permissions_stack = OscarPermissionsStack(
        app, "OscarPermissionsStack",
        env=env,
        description="OSCAR IAM permissions and roles"
    )
    
    # 2. Secrets (AWS Secrets Manager)
    secrets_stack = OscarSecretsStack(
        app, "OscarSecretsStack",
        env=env,
        description="OSCAR secrets management"
    )
    
    # 3. Storage (DynamoDB tables)
    storage_stack = OscarStorageStack(
        app, "OscarStorageStack",
        env=env,
        description="OSCAR DynamoDB storage"
    )
    
    # 4. VPC (if needed for Lambda functions)
    vpc_stack = None
    if os.environ.get("VPC_ID") or os.environ.get("USE_VPC", "false").lower() == "true":
        vpc_stack = OscarVpcStack(
            app, "OscarVpcStack",
            env=env,
            description="OSCAR VPC configuration"
        )
    
    # 5. Knowledge Base (temporarily disabled - will add back later)
    # knowledge_base_stack = OscarKnowledgeBaseStack(
    #     app, "OscarKnowledgeBaseStack",
    #     env=env,
    #     description="OSCAR Bedrock Knowledge Base"
    # )
    knowledge_base_stack = None
    
    # 6. Lambda Functions (before API Gateway)
    lambda_stack = OscarLambdaStack(
        app, "OscarLambdaStack",
        permissions_stack=permissions_stack,
        secrets_stack=secrets_stack,
        vpc_stack=vpc_stack,
        env=env,
        description="OSCAR Lambda functions"
    )
    
    # 7. API Gateway (after Lambda functions)
    api_gateway_stack = OscarApiGatewayStack(
        app, "OscarApiGatewayStack",
        lambda_stack=lambda_stack,
        permissions_stack=permissions_stack,
        env=env,
        description="OSCAR API Gateway"
    )
    
    # 8. Bedrock Agents (will be deployed manually after CDK stacks)
    # agents_stack = OscarAgentsStack(
    #     app, "OscarAgentsStack",
    #     permissions_stack=permissions_stack,
    #     knowledge_base_stack=knowledge_base_stack,
    #     lambda_stack=lambda_stack,
    #     env=env,
    #     description="OSCAR Bedrock agents"
    # )
    agents_stack = None
    
    # Add tags to all stacks
    stacks_to_tag = [permissions_stack, secrets_stack, storage_stack, api_gateway_stack, 
                     lambda_stack]
    if knowledge_base_stack:
        stacks_to_tag.append(knowledge_base_stack)
    if agents_stack:
        stacks_to_tag.append(agents_stack)
    
    for stack in stacks_to_tag:
        Tags.of(stack).add("Project", "OSCAR")
        Tags.of(stack).add("Environment", environment)
        Tags.of(stack).add("ManagedBy", "CDK")
    
    if vpc_stack:
        Tags.of(vpc_stack).add("Project", "OSCAR")
        Tags.of(vpc_stack).add("Environment", environment)
        Tags.of(vpc_stack).add("ManagedBy", "CDK")
    
    # Synthesize the CloudFormation templates
    app.synth()

if __name__ == "__main__":
    main()