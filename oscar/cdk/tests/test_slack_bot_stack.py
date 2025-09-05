#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Tests for the OscarSlackBotStack.
"""

import os
import pytest
from aws_cdk import App
from aws_cdk.assertions import Template, Match

from stacks.slack_bot_stack import OscarSlackBotStack


@pytest.fixture
def app():
    """Create a CDK app fixture."""
    return App()


@pytest.fixture
def stack(app):
    """Create a stack fixture."""
    # Set required environment variables for testing
    os.environ["CDK_DEFAULT_ACCOUNT"] = "123456789012"
    os.environ["CDK_DEFAULT_REGION"] = "us-west-2"
    os.environ["KNOWLEDGE_BASE_ID"] = "test-knowledge-base-id"
    os.environ["MODEL_ARN"] = "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
    
    return OscarSlackBotStack(app, "TestStack")


def test_stack_creates_dynamodb_tables(stack):
    """Test that the stack creates DynamoDB tables."""
    template = Template.from_stack(stack)
    
    # Check that the stack creates DynamoDB tables
    template.resource_count_is("AWS::DynamoDB::Table", 2)
    
    # Check that the tables have the expected properties
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "KeySchema": [
                {
                    "AttributeName": "event_id",
                    "KeyType": "HASH"
                }
            ],
            "AttributeDefinitions": [
                {
                    "AttributeName": "event_id",
                    "AttributeType": "S"
                }
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "TimeToLiveSpecification": {
                "AttributeName": "ttl",
                "Enabled": True
            }
        }
    )
    
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "KeySchema": [
                {
                    "AttributeName": "thread_key",
                    "KeyType": "HASH"
                }
            ],
            "AttributeDefinitions": [
                {
                    "AttributeName": "thread_key",
                    "AttributeType": "S"
                }
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "TimeToLiveSpecification": {
                "AttributeName": "ttl",
                "Enabled": True
            }
        }
    )


def test_stack_creates_lambda_function(stack):
    """Test that the stack creates a Lambda function."""
    template = Template.from_stack(stack)
    
    # Check that the stack creates a Lambda function
    template.resource_count_is("AWS::Lambda::Function", 1)
    
    # Check that the Lambda function has the expected properties
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "app.lambda_handler",
            "Runtime": "python3.12",
            "Timeout": 30,
            "MemorySize": 512
        }
    )


def test_stack_creates_api_gateway(stack):
    """Test that the stack creates an API Gateway."""
    template = Template.from_stack(stack)
    
    # Check that the stack creates an API Gateway
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)
    
    # Check that the API Gateway has at least one method
    # Using direct count check instead of Match.greater_than_or_equal_to for compatibility
    method_count = len(template.find_resources("AWS::ApiGateway::Method"))
    assert method_count >= 1, f"Expected at least 1 API Gateway Method, but found {method_count}"