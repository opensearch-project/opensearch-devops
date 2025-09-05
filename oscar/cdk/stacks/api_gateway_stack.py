#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
API Gateway stack for OSCAR Slack Bot.

This module defines the API Gateway with Slack webhook endpoints, security,
and monitoring for the OSCAR Slack Bot infrastructure.
"""

from typing import Any
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_apigateway as apigateway,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct

class OscarApiGatewayStack(Stack):
    """
    API Gateway stack for OSCAR Slack Bot.
    
    This stack creates and configures the REST API Gateway with Slack webhook
    endpoints, security features, and monitoring capabilities.
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        lambda_stack: Any,
        permissions_stack: Any,
        **kwargs
    ) -> None:
        """
        Initialize API Gateway stack.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            lambda_stack: The Lambda stack with functions
            permissions_stack: The permissions stack with IAM roles
            **kwargs: Additional keyword arguments for Stack
        """
        super().__init__(scope, construct_id, **kwargs)
        
        self.lambda_stack = lambda_stack
        self.permissions_stack = permissions_stack
        
        # Get the main Lambda function and API Gateway role
        self.lambda_function = lambda_stack.lambda_functions["main_agent"]
        self.api_gateway_role = permissions_stack.api_gateway_role
        
        # Create CloudWatch log group for API Gateway
        self.log_group = self._create_log_group()
        
        # Create the REST API Gateway
        self.api = self._create_rest_api()
        
        # Configure Slack webhook endpoints
        self._configure_slack_endpoints()
        
        # Add outputs for important resources
        self._add_outputs()
    
    def _create_log_group(self) -> logs.LogGroup:
        """
        Create CloudWatch log group for API Gateway access logs.
        
        Returns:
            The created CloudWatch log group
        """
        return logs.LogGroup(
            self, "ApiGatewayLogGroup",
            log_group_name="/aws/apigateway/oscar-slack-bot-cdk",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )
    
    def _create_rest_api(self) -> apigateway.RestApi:
        """
        Create the REST API Gateway with security and monitoring configuration.
        
        Returns:
            The created REST API Gateway
        """
        api = apigateway.RestApi(
            self, "OscarSlackBotApi",
            rest_api_name="oscar-slack-bot-api-cdk",
            description="OSCAR Slack Bot API Gateway for webhook endpoints",
            
            # Keep minimal configuration
            deploy_options=apigateway.StageOptions(
                stage_name="prod"
            ),
            
            # CORS disabled for Slack webhook compatibility
            
            # Security configuration
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            
            # Enable execute API endpoint for Slack webhook access
            disable_execute_api_endpoint=False
        )
        
        # Keep it simple - no additional security or monitoring features
        
        return api
    
    def _configure_slack_endpoints(self) -> None:
        """
        Configure Slack webhook endpoints with proper methods and integration.
        """
        # Create /slack resource
        slack_resource = self.api.root.add_resource("slack")
        
        # No request validator to ensure Slack compatibility
        
        # Create Lambda proxy integration (required for Slack challenge handling)
        lambda_integration = apigateway.LambdaIntegration(
            self.lambda_function,
            proxy=True,  # Enable proxy integration for proper request/response handling
            allow_test_invoke=True
        )
        
        # Create /slack/events endpoint with proxy integration (only endpoint needed)
        events_resource = slack_resource.add_resource("events")
        events_resource.add_method(
            "POST",
            lambda_integration,
            authorization_type=apigateway.AuthorizationType.NONE
        )
    



    def _add_outputs(self) -> None:
        """
        Add CloudFormation outputs for important resources.
        """
        CfnOutput(
            self, "ApiGatewayUrl",
            value=self.api.url,
            description="Base URL of the API Gateway"
        )
        
        CfnOutput(
            self, "SlackEventsUrl", 
            value=f"{self.api.url}slack/events",
            description="URL for Slack Events API webhook"
        )
        
        CfnOutput(
            self, "ApiGatewayId",
            value=self.api.rest_api_id,
            description="ID of the API Gateway"
        )