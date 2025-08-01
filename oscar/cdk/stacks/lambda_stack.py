#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Lambda stack for OSCAR Slack Bot.

This module defines the Lambda function, IAM role, and API Gateway used by the OSCAR Slack Bot.
It handles configuration management, security permissions, and resource creation following
AWS best practices.

The stack creates:
- Lambda function with configurable timeout and memory
- IAM role with least-privilege permissions
- API Gateway with CORS configuration
- CloudFormation outputs for integration
"""

import logging
import os
from typing import Dict, List, Optional
from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    CfnOutput
)
from constructs import Construct

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_LAMBDA_TIMEOUT = 30  # seconds
DEFAULT_LAMBDA_MEMORY = 512  # MB
DEFAULT_FUNCTION_NAME = "oscar-slack-bot"
DEFAULT_AWS_REGION = "us-east-1"

# Slack-specific CORS origins
SLACK_CORS_ORIGINS = [
    "https://slack.com",
    "https://*.slack.com", 
    "https://api.slack.com"
]

# Required environment variables for bot functionality
REQUIRED_ENV_VARS = [
    "SLACK_BOT_TOKEN",
    "SLACK_SIGNING_SECRET", 
    "KNOWLEDGE_BASE_ID"
]

class OscarLambdaStack(Construct):
    """
    Lambda resources for OSCAR Slack Bot.
    
    This construct creates and configures:
    - Lambda function with configurable runtime settings
    - IAM role with least-privilege permissions for Bedrock, DynamoDB, and self-invocation
    - API Gateway with Slack-optimized CORS configuration
    - CloudFormation outputs for external integration
    
    The construct follows AWS security best practices and CDK patterns.
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        sessions_table: dynamodb.Table, 
        context_table: dynamodb.Table
    ) -> None:
        """
        Initialize Lambda resources with dependency injection.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct  
            sessions_table: DynamoDB table for session data storage
            context_table: DynamoDB table for conversation context storage
            
        Raises:
            ValueError: If required tables are not provided
        """
        super().__init__(scope, construct_id)
        
        # Validate inputs
        if not sessions_table or not context_table:
            raise ValueError("Both sessions_table and context_table are required")
        
        # Store table references for environment variable configuration
        self.sessions_table = sessions_table
        self.context_table = context_table
        
        # Create resources in dependency order
        logger.info("Creating Lambda stack resources for %s", construct_id)
        
        # 1. Create IAM role with required permissions
        self.lambda_role = self._create_lambda_role()

        # 2. Create Lambda function with role
        self.lambda_function = self._create_lambda_function()

        # 3. Create API Gateway for external access
        self.api = self._create_api_gateway()
        
        # 4. Export important resource information
        self._add_outputs()
        
        logger.info("Lambda stack resources created successfully")
    
    def _create_lambda_role(self) -> iam.Role:
        """
        Create IAM role for Lambda function with least-privilege permissions.
        
        The role includes permissions for:
        - Basic Lambda execution (CloudWatch Logs)
        - Bedrock Knowledge Base operations
        - DynamoDB table access (specific tables only)
        - Self-invocation for async processing
        
        Returns:
            Configured IAM role for the Lambda function
        """
        role = iam.Role(
            self, "OscarLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            description="IAM role for OSCAR Slack Bot Lambda function"
        )

        # Bedrock permissions for AI/ML operations
        self._add_bedrock_permissions(role)
        
        # DynamoDB permissions for data storage
        self._add_dynamodb_permissions(role)
        
        # Self-invocation permissions for async processing
        self._add_lambda_permissions(role)
        
        logger.info("Created Lambda IAM role with required permissions")
        return role
    
    def _add_bedrock_permissions(self, role: iam.Role) -> None:
        """Add Bedrock service permissions to the IAM role."""
        bedrock_actions = [
            "bedrock-agent-runtime:RetrieveAndGenerate",
            "bedrock:RetrieveAndGenerate", 
            "bedrock:Retrieve",
            "bedrock:GetKnowledgeBase",
            "bedrock:InvokeModel",
            "bedrock:GetFoundationModel",
            "bedrock:GetInferenceProfile",
            "bedrock:ListInferenceProfiles"
        ]
        
        role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAccess",
                actions=bedrock_actions,
                resources=["*"],  # Bedrock requires wildcard for some operations
                effect=iam.Effect.ALLOW
            )
        )
    
    def _add_dynamodb_permissions(self, role: iam.Role) -> None:
        """Add DynamoDB permissions for specific tables only."""
        dynamodb_actions = [
            "dynamodb:GetItem",
            "dynamodb:PutItem", 
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem",
            "dynamodb:Query"
        ]
        
        role.add_to_policy(
            iam.PolicyStatement(
                sid="DynamoDBAccess",
                actions=dynamodb_actions,
                resources=[
                    self.sessions_table.table_arn,
                    self.context_table.table_arn
                ],
                effect=iam.Effect.ALLOW
            )
        )
    
    def _add_lambda_permissions(self, role: iam.Role) -> None:
        """Add self-invocation permissions for async processing."""
        # Get function name from context or environment
        app = self.node.root
        function_name = (
            app.node.try_get_context('lambda_function_name') or
            os.environ.get("LAMBDA_FUNCTION_NAME", DEFAULT_FUNCTION_NAME)
        )
        
        role.add_to_policy(
            iam.PolicyStatement(
                sid="SelfInvocation",
                actions=["lambda:InvokeFunction"],
                resources=[f"arn:aws:lambda:*:*:function:{function_name}"],
                effect=iam.Effect.ALLOW
            )
        )
    
    def _create_lambda_function(self) -> lambda_.Function:
        """
        Create Lambda function with configurable runtime settings.
        
        Configuration is sourced from CDK context with fallbacks to environment
        variables and sensible defaults.
        
        Returns:
            Configured Lambda function
        """
        # Get configuration from context with defaults
        app = self.node.root
        config = self._get_lambda_configuration(app)
        
        # Create Lambda function
        function = lambda_.Function(
            self, "OscarSlackBotFunction",
            function_name=config['name'],
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="app.lambda_handler",
            code=lambda_.Code.from_asset("../slack-bot"),
            timeout=Duration.seconds(config['timeout']),
            memory_size=config['memory'],
            environment=self._get_lambda_environment_variables(),
            role=self.lambda_role,
            description=f"OSCAR Slack Bot Lambda function (Stage: {app.node.try_get_context('stage') or 'Dev'})",
            # Enable tracing for better observability
            tracing=lambda_.Tracing.ACTIVE
        )
        
        logger.info("Created Lambda function: %s (timeout: %ds, memory: %dMB)", 
                   config['name'], config['timeout'], config['memory'])
        return function
    
    def _get_lambda_configuration(self, app) -> Dict[str, any]:
        """
        Get Lambda function configuration from context and environment.
        
        Args:
            app: CDK App instance for context access
            
        Returns:
            Dictionary with Lambda configuration parameters
        """
        return {
            'name': (
                app.node.try_get_context('lambda_function_name') or
                os.environ.get("LAMBDA_FUNCTION_NAME", DEFAULT_FUNCTION_NAME)
            ),
            'timeout': app.node.try_get_context('lambda_timeout') or DEFAULT_LAMBDA_TIMEOUT,
            'memory': app.node.try_get_context('lambda_memory') or DEFAULT_LAMBDA_MEMORY
        }
    
    def _create_api_gateway(self) -> apigateway.LambdaRestApi:
        """
        Create the API Gateway for the Lambda function.
        
        Returns:
            The created API Gateway
        """
        # Configure CORS origins with security in mind
        cors_origins = self._get_cors_origins()
        
        api = apigateway.LambdaRestApi(
            self, "OscarSlackBotApi",
            handler=self.lambda_function,
            proxy=False,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=cors_origins,
                allow_methods=["POST"],
                allow_headers=["Content-Type", "X-Slack-Request-Timestamp", "X-Slack-Signature"]
            )
        )

        # Add Slack events endpoint
        slack_events = api.root.add_resource("slack").add_resource("events")
        slack_events.add_method("POST")
        
        return api
    
    def _get_cors_origins(self) -> List[str]:
        """
        Get CORS origins configuration with security best practices.
        
        Combines default Slack origins with any custom origins from context.
        All origins are validated to ensure they use HTTPS.
        
        Returns:
            List of allowed CORS origins
        """
        # Start with secure Slack origins
        origins = SLACK_CORS_ORIGINS.copy()
        
        # Add custom origins from context if provided
        app = self.node.root
        custom_origins_str = app.node.try_get_context('cors_allowed_origins') or ""
        
        if custom_origins_str:
            custom_origins = [
                origin.strip() 
                for origin in custom_origins_str.split(",") 
                if origin.strip()
            ]
            
            # Validate custom origins (must be HTTPS)
            validated_origins = []
            for origin in custom_origins:
                if origin.startswith('https://'):
                    validated_origins.append(origin)
                else:
                    logger.warning("Skipping non-HTTPS CORS origin: %s", origin)
            
            if validated_origins:
                origins.extend(validated_origins)
                logger.info("Added custom CORS origins: %s", validated_origins)
        
        logger.info("Configured CORS origins: %s", origins)
        return origins
    
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
        Build environment variables for Lambda function.
        
        Combines required secrets from environment variables with configuration
        from CDK context. Validates required variables and provides warnings
        for missing configuration.
        
        Returns:
            Dictionary of environment variables for the Lambda function
        """
        # Get AWS region with fallback
        region = os.environ.get("AWS_REGION", DEFAULT_AWS_REGION)
        app = self.node.root
        
        # Build environment variables dictionary
        env_vars = {}
        
        # Add required secrets with validation
        env_vars.update(self._get_required_secrets())
        
        # Add Bedrock configuration
        env_vars.update(self._get_bedrock_config(app, region))
        
        # Add DynamoDB table names (use actual table names from resources)
        env_vars.update({
            "SESSIONS_TABLE_NAME": self.sessions_table.table_name,
            "CONTEXT_TABLE_NAME": self.context_table.table_name,
        })
        
        # Add optional configuration from context
        env_vars.update(self._get_optional_config(app))
        
        # Add large text configuration from environment
        prompt_template = os.environ.get("PROMPT_TEMPLATE")
        if prompt_template:
            env_vars["PROMPT_TEMPLATE"] = prompt_template
            logger.info("Added custom prompt template from environment")
        
        logger.info("Configured %d environment variables for Lambda", len(env_vars))
        return env_vars
    
    def _get_required_secrets(self) -> Dict[str, str]:
        """Get and validate required secret environment variables."""
        secrets = {}
        missing_secrets = []
        
        for var_name in REQUIRED_ENV_VARS:
            value = os.environ.get(var_name, "")
            secrets[var_name] = value
            
            if not value:
                missing_secrets.append(var_name)
        
        # Special handling for KNOWLEDGE_BASE_ID placeholder
        if not secrets["KNOWLEDGE_BASE_ID"]:
            secrets["KNOWLEDGE_BASE_ID"] = "PLACEHOLDER_KNOWLEDGE_BASE_ID"
            logger.warning("KNOWLEDGE_BASE_ID not set, using placeholder. Bot will not function until configured.")
        
        if missing_secrets:
            logger.warning("Missing required environment variables: %s", ', '.join(missing_secrets))
            logger.warning("Bot will not function until these are configured in .env file")
        
        return secrets
    
    def _get_bedrock_config(self, app, region: str) -> Dict[str, str]:
        """Get Bedrock model configuration."""
        model_arn = app.node.try_get_context('model_arn')
        if not model_arn:
            model_arn = f'arn:aws:bedrock:{region}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0'
            logger.info("Using default Bedrock model: Claude 3.5 Haiku")
        else:
            logger.info("Using configured Bedrock model from context")
        
        return {"MODEL_ARN": model_arn}
    
    def _get_optional_config(self, app) -> Dict[str, str]:
        """Get optional configuration parameters from context."""
        # Mapping of context keys to environment variable names and defaults
        config_mapping = {
            'dedup_ttl': ('DEDUP_TTL', '300'),
            'session_ttl': ('SESSION_TTL', '3600'), 
            'context_ttl': ('CONTEXT_TTL', '604800'),
            'max_context_length': ('MAX_CONTEXT_LENGTH', '3000'),
            'context_summary_length': ('CONTEXT_SUMMARY_LENGTH', '500'),
            'enable_dm': ('ENABLE_DM', 'false')
        }
        
        config = {}
        for context_key, (env_key, default_value) in config_mapping.items():
            value = app.node.try_get_context(context_key) or default_value
            config[env_key] = str(value)
        
        return config