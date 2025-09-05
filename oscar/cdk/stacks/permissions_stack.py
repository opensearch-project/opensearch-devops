#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Permissions stack for OSCAR CDK automation.

This module defines IAM roles and policies for all OSCAR components including
Bedrock agents, Lambda functions, API Gateway, and cross-account access.
"""

import os
from typing import Dict, List
from aws_cdk import (
    Stack,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct
from .policy_definitions import OscarPolicyDefinitions


class OscarPermissionsStack(Stack):
    """
    IAM permissions and roles for OSCAR infrastructure.
    
    This construct creates all necessary IAM roles and policies for OSCAR components
    with least-privilege access and proper security boundaries.
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize permissions stack.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Get account ID and region from environment
        self.account_id = os.environ.get("CDK_DEFAULT_ACCOUNT")
        self.aws_region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
        
        # Initialize policy definitions
        self.policy_definitions = OscarPolicyDefinitions(self.account_id, self.aws_region)
        
        # Create IAM roles
        self.bedrock_agent_role = self._create_bedrock_agent_role()
        self.lambda_execution_roles = self._create_lambda_execution_roles()
        self.api_gateway_role = self._create_api_gateway_role()
        
        # Create outputs
        self._create_outputs()
    
    def _create_bedrock_agent_role(self) -> iam.Role:
        """
        Create Bedrock agent execution role with proper trust policy and permissions.
        
        Returns:
            The Bedrock agent execution role
        """
        # Trust policy is handled by assumed_by parameter
        
        # Create the role
        role = iam.Role(
            self, "BedrockAgentExecutionRole",
            role_name="oscar-bedrock-agent-execution-role-cdk",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Execution role for OSCAR Bedrock agents"
        )
        
        # Add least-privilege policies for Bedrock agents
        for policy_statement in self.policy_definitions.get_bedrock_agent_policies():
            role.add_to_policy(policy_statement)
        
        return role
    
    def _create_lambda_execution_roles(self) -> Dict[str, iam.Role]:
        """
        Create Lambda execution roles for different function types.
        
        Returns:
            Dictionary of Lambda execution roles by function type
        """
        roles = {}
        
        # Base Lambda execution role for non-VPC functions
        base_role = self._create_base_lambda_role()
        roles["base"] = base_role
        
        # Use existing VPC Lambda execution role for metrics functions
        # This role is pre-authorized for cross-account access to OpenSearch
        vpc_role = iam.Role.from_role_arn(
            self, "ExistingVpcLambdaRole",
            role_arn="arn:aws:iam::395380602281:role/oscar-metrics-lambda-vpc-role"
        )
        roles["vpc"] = vpc_role
        
        # Communication handler role
        communication_role = self._create_communication_handler_role()
        roles["communication"] = communication_role
        
        # Jenkins agent role
        jenkins_role = self._create_jenkins_lambda_role()
        roles["jenkins"] = jenkins_role
        
        return roles
    
    def _create_base_lambda_role(self) -> iam.Role:
        """
        Create base Lambda execution role for standard functions.
        
        Returns:
            The base Lambda execution role
        """
        role = iam.Role(
            self, "BaseLambdaExecutionRole",
            role_name="oscar-lambda-execution-role-cdk",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
            description="Base execution role for OSCAR Lambda functions"
        )
        
        # Add least-privilege policies for base Lambda functions
        for policy_statement in self.policy_definitions.get_lambda_base_policies():
            role.add_to_policy(policy_statement)
        
        return role
    

    
    def _create_communication_handler_role(self) -> iam.Role:
        """
        Create communication handler Lambda execution role.
        
        Returns:
            The communication handler execution role
        """
        role = iam.Role(
            self, "CommunicationHandlerRole",
            role_name="oscar-communication-handler-execution-role-cdk",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
            description="Execution role for OSCAR communication handler Lambda"
        )
        
        # Add least-privilege policies for communication handler
        for policy_statement in self.policy_definitions.get_communication_handler_policies():
            role.add_to_policy(policy_statement)
        
        return role
    
    def _create_jenkins_lambda_role(self) -> iam.Role:
        """
        Create Jenkins Lambda execution role.
        
        Returns:
            The Jenkins Lambda execution role
        """
        role = iam.Role(
            self, "JenkinsLambdaRole",
            role_name="oscar-jenkins-lambda-execution-role-cdk",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
            description="Execution role for OSCAR Jenkins Lambda function"
        )
        
        # Add least-privilege policies for Jenkins Lambda
        for policy_statement in self.policy_definitions.get_jenkins_lambda_policies():
            role.add_to_policy(policy_statement)
        
        return role
    
    def _create_api_gateway_role(self) -> iam.Role:
        """
        Create API Gateway execution role.
        
        Returns:
            The API Gateway execution role
        """
        role = iam.Role(
            self, "ApiGatewayExecutionRole",
            role_name="oscar-api-gateway-execution-role-cdk",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            description="Execution role for OSCAR API Gateway"
        )
        
        # Add least-privilege policies for API Gateway
        for policy_statement in self.policy_definitions.get_api_gateway_policies():
            role.add_to_policy(policy_statement)
        
        return role
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for the IAM roles."""
        # Bedrock agent role output
        CfnOutput(
            self, "BedrockAgentRoleArn",
            value=self.bedrock_agent_role.role_arn,
            description="ARN of the Bedrock agent execution role"
        )
        
        # Lambda execution roles outputs
        for role_type, role in self.lambda_execution_roles.items():
            CfnOutput(
                self, f"LambdaExecutionRole{role_type.title()}Arn",
                value=role.role_arn,
                description=f"ARN of the {role_type} Lambda execution role"
            )
        
        # API Gateway role output
        CfnOutput(
            self, "ApiGatewayRoleArn",
            value=self.api_gateway_role.role_arn,
            description="ARN of the API Gateway execution role"
        )