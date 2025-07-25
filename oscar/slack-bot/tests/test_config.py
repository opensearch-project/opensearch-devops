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

# Set required environment variables before importing config
os.environ.setdefault('KNOWLEDGE_BASE_ID', 'test-kb-id')
os.environ.setdefault('SLACK_BOT_TOKEN', 'test-bot-token')
os.environ.setdefault('SLACK_SIGNING_SECRET', 'test-signing-secret')

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
        """Test that Config initializes and reads from environment variables correctly."""
        # Set TTL values explicitly for testing
        os.environ['DEDUP_TTL'] = '300'
        os.environ['SESSION_TTL'] = '3600'
        os.environ['CONTEXT_TTL'] = '604800'
        os.environ['MAX_CONTEXT_LENGTH'] = '3000'
        os.environ['CONTEXT_SUMMARY_LENGTH'] = '500'
        
        # Create a new Config instance
        test_config = Config(validate_required=True)
        
        # Test that config reads from environment variables we set
        self.assertEqual(test_config.region, os.environ['AWS_REGION'])
        self.assertEqual(test_config.knowledge_base_id, os.environ['KNOWLEDGE_BASE_ID'])
        self.assertEqual(test_config.model_arn, os.environ['MODEL_ARN'])
        self.assertEqual(test_config.sessions_table_name, os.environ['SESSIONS_TABLE_NAME'])
        self.assertEqual(test_config.context_table_name, os.environ['CONTEXT_TABLE_NAME'])
        self.assertEqual(test_config.slack_bot_token, os.environ['SLACK_BOT_TOKEN'])
        self.assertEqual(test_config.slack_signing_secret, os.environ['SLACK_SIGNING_SECRET'])
        
        # Test TTL values are converted to integers correctly
        self.assertEqual(test_config.dedup_ttl, int(os.environ['DEDUP_TTL']))
        self.assertEqual(test_config.session_ttl, int(os.environ['SESSION_TTL']))
        self.assertEqual(test_config.context_ttl, int(os.environ['CONTEXT_TTL']))
        self.assertEqual(test_config.max_context_length, int(os.environ['MAX_CONTEXT_LENGTH']))
        self.assertEqual(test_config.context_summary_length, int(os.environ['CONTEXT_SUMMARY_LENGTH']))
        
        # Test that prompt template contains expected placeholders
        self.assertIn("$query$", test_config.prompt_template)
        self.assertIn("$search_results$", test_config.prompt_template)
    
    def test_config_defaults(self):
        """Test that Config uses appropriate default values when environment variables are not set."""
        # Remove optional environment variables to test defaults
        optional_vars = ['AWS_REGION', 'SESSIONS_TABLE_NAME', 'CONTEXT_TABLE_NAME', 
                        'DEDUP_TTL', 'SESSION_TTL', 'CONTEXT_TTL', 
                        'MAX_CONTEXT_LENGTH', 'CONTEXT_SUMMARY_LENGTH', 'ENABLE_DM']
        
        saved_values = {}
        for var in optional_vars:
            saved_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            test_config = Config(validate_required=True)
            
            # Test default values
            self.assertEqual(test_config.region, 'us-east-1')  # Default region
            self.assertEqual(test_config.sessions_table_name, 'oscar-sessions')
            self.assertEqual(test_config.context_table_name, 'oscar-context')
            self.assertEqual(test_config.dedup_ttl, 300)  # 5 minutes
            self.assertEqual(test_config.session_ttl, 3600)  # 1 hour
            self.assertEqual(test_config.context_ttl, 604800)  # 7 days
            self.assertEqual(test_config.max_context_length, 3000)
            self.assertEqual(test_config.context_summary_length, 500)
            self.assertFalse(test_config.enable_dm)  # Default is false
            
        finally:
            # Restore original values
            for var, value in saved_values.items():
                if value is not None:
                    os.environ[var] = value
        
    def test_config_validation(self):
        """Test that Config validates required environment variables."""
        # Test each required environment variable
        required_vars = ['KNOWLEDGE_BASE_ID', 'SLACK_BOT_TOKEN', 'SLACK_SIGNING_SECRET']
        
        for var in required_vars:
            # Save the current value
            original_value = os.environ.get(var)
            
            try:
                # Remove the required environment variable
                if var in os.environ:
                    del os.environ[var]
                
                # Create a new Config instance with validation enabled
                with self.assertRaises(ValueError) as context:
                    Config(validate_required=True)
                
                self.assertIn(f"{var} environment variable is required", str(context.exception))
                
            finally:
                # Restore the original value
                if original_value is not None:
                    os.environ[var] = original_value
        
        # Test with validation disabled - should not raise errors
        # Temporarily remove a required variable
        original_kb_id = os.environ.get('KNOWLEDGE_BASE_ID')
        if 'KNOWLEDGE_BASE_ID' in os.environ:
            del os.environ['KNOWLEDGE_BASE_ID']
        
        try:
            config_no_validation = Config(validate_required=False)
            self.assertIsNone(config_no_validation.knowledge_base_id)
        finally:
            # Restore the original value
            if original_kb_id is not None:
                os.environ['KNOWLEDGE_BASE_ID'] = original_kb_id

if __name__ == '__main__':
    unittest.main()