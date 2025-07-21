#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Main CDK application for OSCAR Slack Bot.

This module defines the main CDK application that deploys the OSCAR Slack Bot stack.
"""

import os
import sys
from typing import Optional
from aws_cdk import (
    App,
    Environment,
    Tags
)
from stacks.oscar_slack_bot_stack import OscarSlackBotStack

def main() -> None:
    """
    Deploy the OSCAR Slack Bot stack.
    
    This function initializes the CDK app, creates the main stack, and synthesizes
    the CloudFormation template. It validates the AWS region and applies standard
    tags to all resources.
    
    Returns:
        None
    
    Raises:
        SystemExit: If the AWS region is not set to the expected value
    """
    app = App()

    # Get account and region from environment variables
    account: Optional[str] = os.environ.get("CDK_DEFAULT_ACCOUNT")
    region: Optional[str] = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")

    print(f"Deploying to account: {account}")
    print(f"Deploying to region: {region}")

    # Validate region - make configurable but with a default
    default_region: str = "us-east-1"
    expected_region: str = os.environ.get("AWS_REGION", default_region)
    
    if region != expected_region:
        print(f"ERROR: Region is set to {region}, but should be {expected_region}")
        print("Please make sure CDK_DEFAULT_REGION or AWS_REGION is set correctly")
        sys.exit(1)

    # Deploy the main stack
    stack = OscarSlackBotStack(
        app, 
        "OscarSlackBotStack",
        env=Environment(
            account=account,
            region=region
        ),
        description="OSCAR Slack Bot infrastructure for OpenSearch release management"
    )
    
    # Add tags to all resources
    Tags.of(stack).add("Project", "OSCAR")
    Tags.of(stack).add("Service", "SlackBot")
    Tags.of(stack).add("Environment", os.environ.get("ENVIRONMENT", "dev"))
    
    # Synthesize the CloudFormation template
    app.synth()

if __name__ == "__main__":
    main()