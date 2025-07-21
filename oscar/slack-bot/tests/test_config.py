#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Tests for the config module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import sys
import json

# Add the parent directory to sys.path to import the modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import the Config class directly
from config import Config

class TestConfig(unittest.TestCase):
    """Test cases for the Config class."""
    
    def setUp(self):
        """Set up test environment."""
        # Save original environment variables
        self.original_env = os.environ.copy()
        
        # Set test environment variables
        os.environ['AWS_REGION'] = 'us-west-2'
        os.environ['KNOWLEDGE_BASE_ID'] = 'test-kb-id'
        os.environ['MODEL_ARN'] = 'test-model-arn'
        os.environ['SESSIONS_TABLE_NAME'] = 'test-sessions'
        os.environ['CONTEXT_TABLE_NAME'] = 'test-context'
        os.environ['SLACK_BOT_TOKEN'] = 'test-bot-token'
        os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret'
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_config_initialization(self):
        """Test that Config initializes with correct values from environment."""
        # Set TTL values explicitly for testing
        os.environ['DEDUP_TTL'] = '300'
        os.environ['SESSION_TTL'] = '3600'
        os.environ['CONTEXT_TTL'] = '604800'
        os.environ['MAX_CONTEXT_LENGTH'] = '3000'
        os.environ['CONTEXT_SUMMARY_LENGTH'] = '500'
        
        # Create a new Config instance with validation disabled for testing
        test_config = Config(validate_required=True)
        
        self.assertEqual(test_config.region, 'us-west-2')
        self.assertEqual(test_config.knowledge_base_id, 'test-kb-id')
        self.assertEqual(test_config.model_arn, 'test-model-arn')
        self.assertEqual(test_config.sessions_table_name, 'test-sessions')
        self.assertEqual(test_config.context_table_name, 'test-context')
        self.assertEqual(test_config.dedup_ttl, 300)
        self.assertEqual(test_config.session_ttl, 3600)
        self.assertEqual(test_config.context_ttl, 604800)
        self.assertEqual(test_config.max_context_length, 3000)
        self.assertEqual(test_config.context_summary_length, 500)
        self.assertIn("Human: $query$", test_config.prompt_template)
        self.assertIn("Assistant:", test_config.prompt_template)
        
    def test_config_validation(self):
        """Test that Config validates required environment variables."""
        # Save the current environment variables
        saved_env = os.environ.copy()
        
        try:
            # Remove required environment variables
            os.environ.pop('SLACK_BOT_TOKEN', None)
            
            # Create a new Config instance with validation enabled
            with self.assertRaises(ValueError) as context:
                Config(validate_required=True)
            
            self.assertIn("SLACK_BOT_TOKEN environment variable is required", str(context.exception))
            
            # Restore SLACK_BOT_TOKEN but remove SLACK_SIGNING_SECRET
            os.environ['SLACK_BOT_TOKEN'] = 'test-bot-token'
            os.environ.pop('SLACK_SIGNING_SECRET', None)
            
            with self.assertRaises(ValueError) as context:
                Config(validate_required=True)
            
            self.assertIn("SLACK_SIGNING_SECRET environment variable is required", str(context.exception))
            
            # Restore SLACK_SIGNING_SECRET but remove KNOWLEDGE_BASE_ID
            os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret'
            os.environ.pop('KNOWLEDGE_BASE_ID', None)
            
            with self.assertRaises(ValueError) as context:
                Config(validate_required=True)
            
            self.assertIn("KNOWLEDGE_BASE_ID environment variable is required", str(context.exception))
            
            # Test with validation disabled
            config_no_validation = Config(validate_required=False)
            self.assertIsNone(config_no_validation.knowledge_base_id)
            
        finally:
            # Restore the original environment variables
            os.environ.clear()
            os.environ.update(saved_env)

if __name__ == '__main__':
    unittest.main()