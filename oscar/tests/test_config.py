#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Unit tests for configuration management.
"""

import pytest
import os
from unittest.mock import patch
import sys
import os
sys.path.append('oscar-agent')

# Set environment variable before importing config
os.environ['DISABLE_CONFIG_VALIDATION'] = 'true'

from config import Config


class TestConfig:
    """Test cases for Config class."""
    
    def test_config_initialization_with_defaults(self, mock_env_vars):
        """Test config initialization with default values."""
        config = Config(validate_required=False)
        
        assert config.region == 'us-east-1'
        assert config.slack_bot_token == 'xoxb-test-token'
        assert config.slack_signing_secret == 'test-signing-secret'
    
    def test_config_with_custom_region(self):
        """Test config with custom AWS region."""
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2'}):
            config = Config(validate_required=False)
            assert config.region == 'us-west-2'
    
    def test_config_missing_required_vars(self):
        """Test config validation with missing required variables."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                Config(validate_required=True)
    
    def test_config_bedrock_settings(self, mock_env_vars):
        """Test Bedrock-specific configuration."""
        with patch.dict(os.environ, {
            'OSCAR_BEDROCK_AGENT_ID': 'test-agent-id',
            'OSCAR_BEDROCK_AGENT_ALIAS_ID': 'test-alias-id'
        }, clear=False):
            config = Config(validate_required=False)
            assert config.oscar_bedrock_agent_id == 'test-agent-id'
            assert config.oscar_bedrock_agent_alias_id == 'test-alias-id'
    
    def test_config_table_names(self, mock_env_vars):
        """Test DynamoDB table name configuration."""
        config = Config(validate_required=False)
        assert config.sessions_table_name == 'test-sessions'
        assert config.context_table_name == 'test-context'