#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Main stack for OSCAR Slack Bot.

This module defines the main CDK stack that combines all components of the OSCAR Slack Bot.
"""

from aws_cdk import (
    Stack,
    CfnOutput
)
from constructs import Construct
from .storage_stack import OscarStorageStack
from .lambda_stack import OscarLambdaStack

class OscarSlackBotStack(Stack):
    """
    Main stack for OSCAR Slack Bot.
    
    This stack serves as the parent stack that combines all components
    of the OSCAR Slack Bot infrastructure, including storage resources
    and Lambda functions.
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize the OSCAR Slack Bot stack.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            **kwargs: Additional keyword arguments passed to the parent Stack class
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Create storage resources (DynamoDB tables only)
        storage_stack = OscarStorageStack(self, "StorageStack")
        
        # Create Lambda function and API Gateway
        lambda_stack = OscarLambdaStack(
            self, 
            "LambdaStack",
            sessions_table=storage_stack.sessions_table,
            context_table=storage_stack.context_table
        )
        
        # Export important outputs
        CfnOutput(
            self, 
            "SlackBotApiUrl",
            value=lambda_stack.api.url,
            description="Base URL of the API Gateway endpoint"
        )
        
        CfnOutput(
            self, 
            "SlackBotFunctionName",
            value=lambda_stack.lambda_function.function_name,
            description="Name of the Lambda function"
        )