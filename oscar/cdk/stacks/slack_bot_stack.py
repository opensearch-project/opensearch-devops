#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Main stack for OSCAR Slack Bot.

This module defines the main CDK stack that orchestrates all components of the 
OSCAR Slack Bot infrastructure. It combines storage and compute resources into
a cohesive deployment unit.

Architecture:
- Storage Stack: DynamoDB tables for data persistence
- Lambda Stack: Function, IAM role, and API Gateway for bot logic
- Integration: Proper dependency management and resource sharing
"""

import logging
from aws_cdk import (
    Stack,
    CfnOutput
)
from constructs import Construct
from .storage_stack import OscarStorageStack
from .lambda_stack import OscarLambdaStack

# Configure logging
logger = logging.getLogger(__name__)

class OscarSlackBotStack(Stack):
    """
    Main orchestration stack for OSCAR Slack Bot.
    
    This stack coordinates the deployment of all OSCAR Slack Bot components:
    - Storage layer (DynamoDB tables)
    - Compute layer (Lambda function with IAM role)
    - API layer (API Gateway with CORS configuration)
    
    The stack ensures proper dependency management and resource integration
    while providing essential outputs for external integration.
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize the OSCAR Slack Bot stack with all components.
        
        Creates storage and compute resources in the correct dependency order,
        ensuring that tables are available before Lambda function creation.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            **kwargs: Additional keyword arguments (env, description, etc.)
        """
        super().__init__(scope, construct_id, **kwargs)
        
        logger.info("Initializing OSCAR Slack Bot stack: %s", construct_id)
        
        # Create storage layer first (no dependencies)
        self.storage_stack = OscarStorageStack(self, "StorageStack")
        
        # Create compute layer with storage dependencies
        self.lambda_stack = OscarLambdaStack(
            self, 
            "LambdaStack",
            sessions_table=self.storage_stack.sessions_table,
            context_table=self.storage_stack.context_table
        )
        
        # Export integration endpoints and identifiers
        self._add_stack_outputs()
        
        logger.info("OSCAR Slack Bot stack initialized successfully")
    
    def _add_stack_outputs(self) -> None:
        """
        Add CloudFormation outputs for external integration.
        
        Exports key identifiers and endpoints that external systems
        need to integrate with the Slack bot.
        """
        # API Gateway endpoint for Slack webhook configuration
        CfnOutput(
            self, 
            "SlackBotApiUrl",
            value=self.lambda_stack.api.url,
            description="Base URL of the API Gateway endpoint for Slack webhook configuration",
            export_name=f"{self.stack_name}-ApiUrl"
        )
        
        # Lambda function name for direct invocation or monitoring
        CfnOutput(
            self, 
            "SlackBotFunctionName",
            value=self.lambda_stack.lambda_function.function_name,
            description="Name of the Lambda function for monitoring and direct invocation",
            export_name=f"{self.stack_name}-FunctionName"
        )
        
        # Webhook URL for easy Slack configuration
        CfnOutput(
            self,
            "SlackWebhookEndpoint", 
            value=f"{self.lambda_stack.api.url}slack/events",
            description="Complete webhook URL to configure in Slack Events API",
            export_name=f"{self.stack_name}-WebhookUrl"
        )
        
        logger.info("Added stack outputs for external integration")