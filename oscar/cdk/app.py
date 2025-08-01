#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Main CDK application for OSCAR Slack Bot.

This module defines the main CDK application that deploys the OSCAR Slack Bot stack.
It handles context validation, environment configuration, and resource tagging.

Example:
    Deploy the stack with default configuration:
        $ python app.py
    
    Deploy with custom stage:
        $ cdk deploy -c stage=Prod
"""

import logging
import os
import sys
from typing import Optional, List
from aws_cdk import (
    App,
    Environment,
    Tags
)
from stacks.slack_bot_stack import OscarSlackBotStack

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants for validation
VALID_STAGES: List[str] = ['Beta', 'Prod', 'Dev']
LAMBDA_TIMEOUT_RANGE = (1, 900)  # seconds
LAMBDA_MEMORY_RANGE = (128, 10240)  # MB
DEFAULT_REGION = "us-east-1"

def _validate_context_parameters(app: App) -> str:
    """
    Validate CDK context parameters.
    
    Args:
        app: The CDK App instance
        
    Returns:
        The validated stage value
        
    Raises:
        SystemExit: If validation fails
    """
    # Validate required stage parameter
    stage = app.node.try_get_context('stage')
    if stage is None:
        logger.error("Missing required 'stage' parameter. Please provide via cdk.context.json or -c stage=Dev")
        logger.error("Valid stages: %s", ', '.join(VALID_STAGES))
        sys.exit(1)
    elif stage not in VALID_STAGES:
        logger.error("Invalid stage '%s'. Must be one of: %s", stage, ', '.join(VALID_STAGES))
        sys.exit(1)
    
    # Validate Lambda timeout if provided
    lambda_timeout = app.node.try_get_context('lambda_timeout')
    if lambda_timeout is not None:
        if not isinstance(lambda_timeout, int) or not (LAMBDA_TIMEOUT_RANGE[0] <= lambda_timeout <= LAMBDA_TIMEOUT_RANGE[1]):
            logger.error("lambda_timeout must be an integer between %d and %d seconds", 
                        LAMBDA_TIMEOUT_RANGE[0], LAMBDA_TIMEOUT_RANGE[1])
            sys.exit(1)
        
    # Validate Lambda memory if provided
    lambda_memory = app.node.try_get_context('lambda_memory')
    if lambda_memory is not None:
        if not isinstance(lambda_memory, int) or not (LAMBDA_MEMORY_RANGE[0] <= lambda_memory <= LAMBDA_MEMORY_RANGE[1]):
            logger.error("lambda_memory must be an integer between %d and %d MB", 
                        LAMBDA_MEMORY_RANGE[0], LAMBDA_MEMORY_RANGE[1])
            sys.exit(1)
    
    logger.info("Context validation passed for stage: %s", stage)
    return stage


def _get_deployment_environment() -> tuple[Optional[str], str]:
    """
    Get AWS account and region for deployment.
    
    Returns:
        Tuple of (account_id, region)
    """
    account = os.environ.get("CDK_DEFAULT_ACCOUNT")
    region = os.environ.get("CDK_DEFAULT_REGION", DEFAULT_REGION)
    
    if not region:
        region = DEFAULT_REGION
        logger.info("No region specified, using default: %s", region)
    
    logger.info("Deployment target - Account: %s, Region: %s", account or "default", region)
    return account, region


def _apply_resource_tags(stack: OscarSlackBotStack, stage: str) -> None:
    """
    Apply standard tags to all stack resources.
    
    Args:
        stack: The CDK stack to tag
        stage: The deployment stage
    """
    tags = {
        "Project": "OSCAR",
        "Service": "SlackBot", 
        "Environment": stage.lower(),
        "ManagedBy": "CDK",
        "Repository": "opensearch-ci"
    }
    
    for key, value in tags.items():
        Tags.of(stack).add(key, value)
    
    logger.info("Applied tags: %s", tags)


def main() -> None:
    """
    Deploy the OSCAR Slack Bot stack.
    
    This function:
    1. Initializes the CDK app
    2. Validates context parameters
    3. Creates the main stack with proper configuration
    4. Applies resource tags
    5. Synthesizes the CloudFormation template
    
    Raises:
        SystemExit: If validation fails or deployment cannot proceed
    """
    logger.info("Starting OSCAR Slack Bot CDK deployment")
    
    try:
        # Initialize CDK app
        app = App()
        
        # Validate context parameters
        stage = _validate_context_parameters(app)
        
        # Get deployment environment
        account, region = _get_deployment_environment()
        
        # Create the main stack
        stack = OscarSlackBotStack(
            app, 
            "OscarSlackBotStack",
            env=Environment(account=account, region=region),
            description=f"OSCAR Slack Bot infrastructure for OpenSearch release management (Stage: {stage})"
        )
        
        # Apply resource tags
        _apply_resource_tags(stack, stage)
        
        # Synthesize the CloudFormation template
        logger.info("Synthesizing CloudFormation template")
        app.synth()
        
        logger.info("CDK deployment preparation completed successfully")
        
    except Exception as e:
        logger.error("CDK deployment failed: %s", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()