#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Pytest configuration file for OSCAR tests.

This file sets up the test environment with required environment variables.
"""

import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment with required environment variables.
    This fixture runs automatically for all tests.
    """
    # Save original environment variables
    original_env = os.environ.copy()
    
    # Set required environment variables for testing
    os.environ['AWS_REGION'] = 'us-west-2'
    os.environ['KNOWLEDGE_BASE_ID'] = 'test-kb-id'
    os.environ['MODEL_ARN'] = 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0'
    os.environ['SLACK_BOT_TOKEN'] = 'test-bot-token'
    os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret'
    os.environ['SESSIONS_TABLE_NAME'] = 'test-sessions'
    os.environ['CONTEXT_TABLE_NAME'] = 'test-context'
    os.environ['DEDUP_TTL'] = '300'
    os.environ['SESSION_TTL'] = '3600'
    os.environ['CONTEXT_TTL'] = '604800'
    os.environ['MAX_CONTEXT_LENGTH'] = '3000'
    os.environ['CONTEXT_SUMMARY_LENGTH'] = '500'
    os.environ['ENABLE_DM'] = 'false'
    
    yield
    
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)