#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
from unittest.mock import Mock, patch


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        'DISABLE_CONFIG_VALIDATION': 'true',
        'SLACK_BOT_TOKEN': 'xoxb-test-token',
        'SLACK_SIGNING_SECRET': 'test-signing-secret',
        'KNOWLEDGE_BASE_ID': 'test-kb-id',
        'MODEL_ARN': 'arn:aws:bedrock:us-east-1::foundation-model/test-model',
        'AWS_REGION': 'us-east-1',
        'SESSIONS_TABLE_NAME': 'test-sessions',
        'CONTEXT_TABLE_NAME': 'test-context',
        'OSCAR_BEDROCK_AGENT_ID': 'test-agent-id',
        'OSCAR_BEDROCK_AGENT_ALIAS_ID': 'test-alias-id'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_slack_event():
    """Mock Slack event for testing."""
    return {
        'type': 'event_callback',
        'event': {
            'type': 'app_mention',
            'user': 'U123456',
            'text': '<@U987654> Hello OSCAR!',
            'channel': 'C123456',
            'ts': '1234567890.123456',
            'thread_ts': '1234567890.123456'
        },
        'team_id': 'T123456',
        'api_app_id': 'A123456'
    }


@pytest.fixture
def mock_lambda_context():
    """Mock AWS Lambda context."""
    context = Mock()
    context.function_name = 'test-function'
    context.function_version = '1'
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    context.memory_limit_in_mb = 128
    context.remaining_time_in_millis = lambda: 30000
    context.log_group_name = '/aws/lambda/test-function'
    context.log_stream_name = '2023/01/01/[$LATEST]test'
    context.aws_request_id = 'test-request-id'
    return context


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client for testing."""
    client = Mock()
    client.retrieve_and_generate.return_value = {
        'output': {
            'text': 'Test response from Bedrock'
        },
        'citations': []
    }
    return client


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB table for testing."""
    table = Mock()
    table.put_item.return_value = {}
    table.get_item.return_value = {'Item': {'context': 'test context'}}
    table.update_item.return_value = {}
    return table