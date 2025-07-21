#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Lambda stack for OSCAR Slack Bot.

This module defines the Lambda function and API Gateway used by the OSCAR Slack Bot.
"""

import os
from typing import Dict, Any, Optional
from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    CfnOutput
)
from constructs import Construct

class OscarLambdaStack(Construct):
    """
    Lambda resources for OSCAR Slack Bot.
    
    This construct creates and configures the Lambda function, IAM role,
    and API Gateway for the OSCAR Slack Bot.
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        sessions_table: dynamodb.Table, 
        context_table: dynamodb.Table
    ) -> None:
        """
        Initialize Lambda resources.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            sessions_table: The DynamoDB table for session data
            context_table: The DynamoDB table for context data
        """
        super().__init__(scope, construct_id)
        
        # Create Lambda function role with appropriate permissions
        self.lambda_role = self._create_lambda_role(sessions_table, context_table)

        # Create Lambda function with placeholder code
        self.lambda_function = self._create_lambda_function()

        # Create API Gateway
        self.api = self._create_api_gateway()
        
        # Add outputs for important resources
        self._add_outputs()
    
    def _create_lambda_role(
        self, 
        sessions_table: dynamodb.Table, 
        context_table: dynamodb.Table
    ) -> iam.Role:
        """
        Create the IAM role for the Lambda function with appropriate permissions.
        
        Args:
            sessions_table: The DynamoDB table for session data
            context_table: The DynamoDB table for context data
            
        Returns:
            The created IAM role
        """
        role = iam.Role(
            self, "OscarLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add permissions for Bedrock
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:Retrieve",
                    "bedrock:GetFoundationModel",
                    "bedrock:ListFoundationModels",
                    "bedrock:GetKnowledgeBase",
                    "bedrock:ListKnowledgeBases",
                    "bedrock:GetInferenceProfile",
                    "bedrock:ListInferenceProfiles",
                    "bedrock-agent-runtime:Retrieve",
                    "bedrock-agent-runtime:RetrieveAndGenerate",
                    "bedrock-agent-runtime:InvokeAgent"
                ],
                resources=["*"]
            )
        )

        # Add permissions for DynamoDB with least privilege
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query"
                ],
                resources=[
                    sessions_table.table_arn,
                    context_table.table_arn
                ]
            )
        )
        
        # Add permissions for Lambda to invoke itself asynchronously
        function_name = os.environ.get("LAMBDA_FUNCTION_NAME", "oscar-slack-bot")
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:InvokeFunction"
                ],
                resources=[
                    f"arn:aws:lambda:*:*:function:{function_name}"
                ]
            )
        )
        
        return role
    
    def _create_lambda_function(self) -> lambda_.Function:
        """
        Create the Lambda function with placeholder code.
        
        Returns:
            The created Lambda function
        """
        function_name = os.environ.get("LAMBDA_FUNCTION_NAME", "oscar-slack-bot")
        
        return lambda_.Function(
            self, "OscarSlackBotFunction",
            function_name=function_name,
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="app.lambda_handler",
            code=lambda_.Code.from_inline("""
import os
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Lambda function deployed successfully. Will be updated with full code.'
    }
"""),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment=self._get_lambda_environment_variables(),
            role=self.lambda_role
        )
    
    def _create_api_gateway(self) -> apigateway.LambdaRestApi:
        """
        Create the API Gateway for the Lambda function.
        
        Returns:
            The created API Gateway
        """
        api = apigateway.LambdaRestApi(
            self, "OscarSlackBotApi",
            handler=self.lambda_function,
            proxy=False,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["POST"]
            )
        )

        # Add Slack events endpoint
        slack_events = api.root.add_resource("slack").add_resource("events")
        slack_events.add_method("POST")
        
        return api
    
    def _add_outputs(self) -> None:
        """
        Add CloudFormation outputs for important resources.
        """
        CfnOutput(
            self, "SlackWebhookUrl",
            value=f"{self.api.url}slack/events",
            description="URL to configure in Slack Events API"
        )
        
        CfnOutput(
            self, "LambdaFunctionName",
            value=self.lambda_function.function_name,
            description="Name of the Lambda function"
        )
        
        CfnOutput(
            self, "LambdaRoleArn",
            value=self.lambda_role.role_arn,
            description="ARN of the Lambda execution role"
        )
    
    def _get_lambda_environment_variables(self) -> Dict[str, str]:
        """
        Get environment variables for Lambda function.
        
        Returns:
            Dictionary of environment variables for the Lambda function
        """
        # Get AWS region with fallback
        region = os.environ.get("AWS_REGION", "us-east-1")
        
        # Define required variables with validation
        knowledge_base_id = os.environ.get("KNOWLEDGE_BASE_ID")
        if not knowledge_base_id:
            knowledge_base_id = "PLACEHOLDER_KNOWLEDGE_BASE_ID"
            print("WARNING: KNOWLEDGE_BASE_ID not set, using placeholder value")
            
        model_arn = os.environ.get("MODEL_ARN")
        if not model_arn:
            model_arn = f'arn:aws:bedrock:{region}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0'
            print(f"WARNING: MODEL_ARN not set, using default Claude 3.5 Haiku model: {model_arn}")
        
        env_vars: Dict[str, str] = {
            # Required configuration
            "KNOWLEDGE_BASE_ID": knowledge_base_id,
            "MODEL_ARN": model_arn,
            "SLACK_BOT_TOKEN": os.environ.get("SLACK_BOT_TOKEN", ""),
            "SLACK_SIGNING_SECRET": os.environ.get("SLACK_SIGNING_SECRET", ""),
            
            # Optional configuration
            # Note: AWS_REGION is a reserved environment variable in Lambda and cannot be set manually
            "SESSIONS_TABLE_NAME": os.environ.get("SESSIONS_TABLE_NAME", "oscar-sessions-v2"),
            "CONTEXT_TABLE_NAME": os.environ.get("CONTEXT_TABLE_NAME", "oscar-context"),
            "DEDUP_TTL": os.environ.get("DEDUP_TTL", "300"),
            "SESSION_TTL": os.environ.get("SESSION_TTL", "3600"),
            "CONTEXT_TTL": os.environ.get("CONTEXT_TTL", "604800"),  # 7 days
            "MAX_CONTEXT_LENGTH": os.environ.get("MAX_CONTEXT_LENGTH", "3000"),
            "CONTEXT_SUMMARY_LENGTH": os.environ.get("CONTEXT_SUMMARY_LENGTH", "500"),
            
            # Feature flags
            "ENABLE_DM": os.environ.get("ENABLE_DM", "false"),
        }
        
        # Add prompt template if provided
        prompt_template = os.environ.get("PROMPT_TEMPLATE")
        if prompt_template:
            env_vars["PROMPT_TEMPLATE"] = prompt_template
            
        return env_vars