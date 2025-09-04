#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Tests for OSCAR permissions stack.

This module contains unit tests for the OscarPermissionsStack to ensure
proper IAM role and policy creation with least-privilege principles.
"""

import os
import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from stacks.permissions_stack import OscarPermissionsStack


class TestOscarPermissionsStack:
    """Test cases for OscarPermissionsStack."""
    
    def setup_method(self):
        """Set up test environment."""
        # Set required environment variables
        os.environ["CDK_DEFAULT_ACCOUNT"] = "123456789012"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
        
        # Create CDK app and stack
        self.app = App()
        self.stack = OscarPermissionsStack(
            self.app, 
            "TestOscarPermissionsStack"
        )
        self.template = Template.from_stack(self.stack)
    
    def test_bedrock_agent_role_creation(self):
        """Test that Bedrock agent execution role is created correctly."""
        # Check that the role exists
        self.template.has_resource_properties("AWS::IAM::Role", {
            "RoleName": "oscar-bedrock-agent-execution-role",
            "AssumeRolePolicyDocument": {
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }
        })
    
    def test_lambda_execution_roles_creation(self):
        """Test that Lambda execution roles are created correctly."""
        # Check base Lambda role
        self.template.has_resource_properties("AWS::IAM::Role", {
            "RoleName": "oscar-lambda-execution-role"
        })
        
        # Check VPC Lambda role
        self.template.has_resource_properties("AWS::IAM::Role", {
            "RoleName": "oscar-vpc-lambda-execution-role"
        })
        
        # Check communication handler role
        self.template.has_resource_properties("AWS::IAM::Role", {
            "RoleName": "oscar-communication-handler-execution-role"
        })
        
        # Check Jenkins Lambda role
        self.template.has_resource_properties("AWS::IAM::Role", {
            "RoleName": "oscar-jenkins-lambda-execution-role"
        })
    
    def test_api_gateway_role_creation(self):
        """Test that API Gateway execution role is created correctly."""
        self.template.has_resource_properties("AWS::IAM::Role", {
            "RoleName": "oscar-api-gateway-execution-role",
            "AssumeRolePolicyDocument": {
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "apigateway.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }
        })
    
    def test_least_privilege_policies(self):
        """Test that policies follow least-privilege principles."""
        # Check that no policies use wildcard resources for sensitive actions
        template_dict = self.template.to_json()
        
        # Look for IAM policies in the template
        for resource_name, resource in template_dict.get("Resources", {}).items():
            if resource.get("Type") == "AWS::IAM::Policy":
                policy_document = resource.get("Properties", {}).get("PolicyDocument", {})
                statements = policy_document.get("Statement", [])
                
                for statement in statements:
                    actions = statement.get("Action", [])
                    resources = statement.get("Resource", [])
                    
                    if isinstance(actions, str):
                        actions = [actions]
                    if isinstance(resources, str):
                        resources = [resources]
                    
                    # Check for dangerous combinations
                    sensitive_actions = [
                        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
                        "lambda:InvokeFunction", "secretsmanager:GetSecretValue"
                    ]
                    
                    for action in actions:
                        if any(sensitive in action for sensitive in sensitive_actions):
                            # These actions should not use wildcard resources
                            assert "*" not in resources, f"Action {action} should not use wildcard resources"
    
    def test_cross_account_access_restrictions(self):
        """Test that cross-account access is properly restricted."""
        # Check that sts:AssumeRole has proper conditions
        template_dict = self.template.to_json()
        
        found_assume_role = False
        for resource_name, resource in template_dict.get("Resources", {}).items():
            if resource.get("Type") == "AWS::IAM::Policy":
                policy_document = resource.get("Properties", {}).get("PolicyDocument", {})
                statements = policy_document.get("Statement", [])
                
                for statement in statements:
                    actions = statement.get("Action", [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    if "sts:AssumeRole" in actions:
                        found_assume_role = True
                        # Should have specific resource ARN
                        resources = statement.get("Resource", [])
                        if isinstance(resources, str):
                            resources = [resources]
                        
                        # Check that it's not a wildcard
                        assert "*" not in resources, "sts:AssumeRole should not use wildcard resources"
                        
                        # Check for specific cross-account role
                        assert any("979020455945" in resource for resource in resources), \
                            "Should reference specific cross-account role"
        
        # We should find at least one sts:AssumeRole statement
        assert found_assume_role, "Should have sts:AssumeRole policy for cross-account access"
    
    def test_secrets_manager_access_restrictions(self):
        """Test that Secrets Manager access is properly restricted."""
        template_dict = self.template.to_json()
        
        found_secrets_access = False
        for resource_name, resource in template_dict.get("Resources", {}).items():
            if resource.get("Type") == "AWS::IAM::Policy":
                policy_document = resource.get("Properties", {}).get("PolicyDocument", {})
                statements = policy_document.get("Statement", [])
                
                for statement in statements:
                    actions = statement.get("Action", [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    if "secretsmanager:GetSecretValue" in actions:
                        found_secrets_access = True
                        resources = statement.get("Resource", [])
                        if isinstance(resources, str):
                            resources = [resources]
                        
                        # Should reference specific OSCAR secrets
                        assert any("oscar-central-env" in resource for resource in resources), \
                            "Should reference oscar-central-env secret"
        
        assert found_secrets_access, "Should have Secrets Manager access policies"
    
    def test_outputs_creation(self):
        """Test that CloudFormation outputs are created."""
        # Check for Bedrock agent role output
        self.template.has_output("BedrockAgentRoleArn")
        
        # Check for Lambda role outputs
        self.template.has_output("LambdaExecutionRoleBaseArn")
        self.template.has_output("LambdaExecutionRoleVpcArn")
        self.template.has_output("LambdaExecutionRoleCommunicationArn")
        self.template.has_output("LambdaExecutionRoleJenkinsArn")
        
        # Check for API Gateway role output
        self.template.has_output("ApiGatewayRoleArn")


if __name__ == "__main__":
    pytest.main([__file__])