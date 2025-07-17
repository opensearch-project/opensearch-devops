"""
Tests for the config module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from oscar.config import Config

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
        os.environ['CONTEXT_TTL'] = '172800'
        os.environ['MAX_CONTEXT_LENGTH'] = '3000'
        os.environ['CONTEXT_SUMMARY_LENGTH'] = '500'
        
        config = Config()
        
        self.assertEqual(config.region, 'us-west-2')
        self.assertEqual(config.knowledge_base_id, 'test-kb-id')
        self.assertEqual(config.model_arn, 'test-model-arn')
        self.assertEqual(config.sessions_table_name, 'test-sessions')
        self.assertEqual(config.context_table_name, 'test-context')
        self.assertEqual(config.dedup_ttl, 300)
        self.assertEqual(config.session_ttl, 3600)
        self.assertEqual(config.context_ttl, 172800)
        self.assertEqual(config.max_context_length, 3000)
        self.assertEqual(config.context_summary_length, 500)
        self.assertIn("Human: $query$", config.prompt_template)
        self.assertIn("Assistant:", config.prompt_template)
    
    def test_config_default_values(self):
        """Test that Config uses default values when environment variables are not set."""
        # Clear specific environment variables
        del os.environ['SESSIONS_TABLE_NAME']
        del os.environ['CONTEXT_TABLE_NAME']
        
        config = Config()
        
        self.assertEqual(config.sessions_table_name, 'oscar-sessions')
        self.assertEqual(config.context_table_name, 'oscar-context')
    
    @patch('boto3.client')
    def test_get_slack_credentials_from_secrets_manager(self, mock_boto_client):
        """Test retrieving Slack credentials from Secrets Manager."""
        # Set up mock
        mock_secrets_client = MagicMock()
        mock_boto_client.return_value = mock_secrets_client
        mock_secrets_client.get_secret_value.return_value = {
            'SecretString': '{"SLACK_BOT_TOKEN": "secret-bot-token", "SLACK_SIGNING_SECRET": "secret-signing-secret"}'
        }
        
        # Set secrets ARN
        os.environ['SLACK_SECRETS_ARN'] = 'test-secrets-arn'
        
        config = Config()
        bot_token, signing_secret = config.get_slack_credentials()
        
        # Verify correct values returned
        self.assertEqual(bot_token, 'secret-bot-token')
        self.assertEqual(signing_secret, 'secret-signing-secret')
        
        # Verify Secrets Manager was called correctly
        mock_boto_client.assert_called_once_with('secretsmanager', region_name='us-west-2')
        mock_secrets_client.get_secret_value.assert_called_once_with(SecretId='test-secrets-arn')
    
    def test_get_slack_credentials_from_environment(self):
        """Test retrieving Slack credentials from environment variables."""
        # Ensure no secrets ARN is set
        if 'SLACK_SECRETS_ARN' in os.environ:
            del os.environ['SLACK_SECRETS_ARN']
        
        config = Config()
        bot_token, signing_secret = config.get_slack_credentials()
        
        # Verify correct values returned from environment
        self.assertEqual(bot_token, 'test-bot-token')
        self.assertEqual(signing_secret, 'test-signing-secret')

if __name__ == '__main__':
    unittest.main()