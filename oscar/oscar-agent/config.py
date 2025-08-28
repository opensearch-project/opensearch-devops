#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Configuration Management for OSCAR Agent.

This module provides centralized configuration management for the OSCAR agent
implementation, handling environment variables, validation, and default values.

Classes:
    Config: Main configuration class with validation and environment variable handling
"""

import logging
import os
from typing import Optional, Tuple
import json
import boto3
from dotenv import load_dotenv
from io import StringIO

logger = logging.getLogger(__name__)

class Config:
    """Centralized configuration management for OSCAR Agent.
    
    This class handles all configuration aspects including environment variables,
    validation, and default values. It supports both Phase 1 (single agent) and
    Phase 2 (multi-agent) configurations.
    """
    
    def __init__(self, validate_required: bool = True) -> None:
        """Initialize configuration with environment variables.
        
        Args:
            validate_required: Whether to validate required environment variables
            
        Raises:
            ValueError: If required environment variables are missing
        """
        # Load environment variables from AWS Secrets Manager
        self._load_env_from_secrets()
        
        # AWS region
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Dual-agent security configuration
        self.oscar_privileged_bedrock_agent_id = os.environ.get('OSCAR_PRIVILEGED_BEDROCK_AGENT_ID', None)
        self.oscar_privileged_bedrock_agent_alias_id = os.environ.get('OSCAR_PRIVILEGED_BEDROCK_AGENT_ALIAS_ID', None)
        self.oscar_limited_bedrock_agent_id = os.environ.get('OSCAR_LIMITED_BEDROCK_AGENT_ID')
        self.oscar_limited_bedrock_agent_alias_id = os.environ.get('OSCAR_LIMITED_BEDROCK_AGENT_ALIAS_ID')
        
        # Only validate Bedrock agent config if we're in the main agent (not communication handler)
        if validate_required and not self.oscar_privileged_bedrock_agent_id:
            logger.error("OSCAR_PRIVILEGED_BEDROCK_AGENT_ID environment variable is required")
            raise ValueError("OSCAR_PRIVILEGED_BEDROCK_AGENT_ID environment variable is required")
            
        if validate_required and not self.oscar_privileged_bedrock_agent_alias_id:
            logger.error("OSCAR_PRIVILEGED_BEDROCK_AGENT_ALIAS_ID environment variable is required")
            raise ValueError("OSCAR_PRIVILEGED_BEDROCK_AGENT_ALIAS_ID environment variable is required")
            
        if validate_required and not self.oscar_limited_bedrock_agent_id:
            logger.error("OSCAR_LIMITED_BEDROCK_AGENT_ID environment variable is required")
            raise ValueError("OSCAR_LIMITED_BEDROCK_AGENT_ID environment variable is required")
            
        if validate_required and not self.oscar_limited_bedrock_agent_alias_id:
            logger.error("OSCAR_LIMITED_BEDROCK_AGENT_ALIAS_ID environment variable is required")
            raise ValueError("OSCAR_LIMITED_BEDROCK_AGENT_ALIAS_ID environment variable is required")
        
        # DynamoDB tables
        self.context_table_name = os.environ.get('CONTEXT_TABLE_NAME', 'oscar-agent-context')
        
        # Slack credentials
        self.slack_bot_token = os.environ.get('SLACK_BOT_TOKEN')
        self.slack_signing_secret = os.environ.get('SLACK_SIGNING_SECRET')
        
        # Only validate Slack credentials if we're in a component that needs them
        if validate_required and not self.slack_bot_token:
            logger.error("SLACK_BOT_TOKEN environment variable is required")
            raise ValueError("SLACK_BOT_TOKEN environment variable is required")
            
        if validate_required and not self.slack_signing_secret:
            logger.error("SLACK_SIGNING_SECRET environment variable is required")
            raise ValueError("SLACK_SIGNING_SECRET environment variable is required")
        
        # TTL settings
        self.session_ttl = int(os.environ.get('SESSION_TTL', 3600))  # 1 hour
        self.context_ttl = int(os.environ.get('CONTEXT_TTL', 604800))  # 7 days
        
        # Context settings
        self.max_context_length = int(os.environ.get('MAX_CONTEXT_LENGTH', 8000))  
        self.context_summary_length = int(os.environ.get('CONTEXT_SUMMARY_LENGTH', 1000)) 
        
        # Feature flags
        self.enable_dm = os.environ.get('ENABLE_DM', 'false').lower() == 'true'
        
        # Agent timeout and retry settings
        self.agent_timeout = int(os.environ.get('AGENT_TIMEOUT', 90)) 
        self.agent_max_retries = int(os.environ.get('AGENT_MAX_RETRIES', 2))
        
        # Timeout thresholds
        self.hourglass_threshold = int(os.environ.get('HOURGLASS_THRESHOLD_SECONDS', 45))
        self.timeout_threshold = int(os.environ.get('TIMEOUT_THRESHOLD_SECONDS', 120))
        
        # Thread pool settings
        self.max_workers = int(os.environ.get('MAX_WORKERS', 100))
        self.max_active_queries = int(os.environ.get('MAX_ACTIVE_QUERIES',  100))
        self.monitor_interval = int(os.environ.get('MONITOR_INTERVAL_SECONDS', 15))
        
        # Thread naming
        self.slack_handler_thread_prefix = os.environ.get('SLACK_HANDLER_THREAD_NAME_PREFIX', 'oscar-agent')
        
        # DM Authorization - users who can DM the bot
        dm_authorized_users = os.environ.get('DM_AUTHORIZED_USERS', '')
        self.dm_authorized_users = [u.strip() for u in dm_authorized_users.split(',') if u.strip()]
        
        channel_allow_list = os.environ.get('CHANNEL_ALLOW_LIST', '')
        self.channel_allow_list = [c.strip() for c in channel_allow_list.split(',') if c.strip()]
        
        # Fully authorized users for dual-agent security
        fully_authorized_users = os.environ.get('FULLY_AUTHORIZED_USERS', '')
        self.fully_authorized_users = [u.strip() for u in fully_authorized_users.split(',') if u.strip()]
        
        # Message formatting
        self.message_preview_length = int(os.environ.get('MESSAGE_PREVIEW_LENGTH', 100))
        self.query_preview_length = int(os.environ.get('QUERY_PREVIEW_LENGTH', 50))
        self.response_preview_length = int(os.environ.get('RESPONSE_PREVIEW_LENGTH', 50))
        
        # Bedrock response configuration
        self.bedrock_message_version = os.environ.get('BEDROCK_RESPONSE_MESSAGE_VERSION', '1.0')
        self.bedrock_action_group = os.environ.get('BEDROCK_ACTION_GROUP_NAME', 'communication-orchestration')
        
        # Agent query templates
        self.agent_queries = {
            'announce': os.environ.get('AGENT_QUERY_ANNOUNCE', ''),
            'assign_owner': os.environ.get('AGENT_QUERY_ASSIGN_OWNER', ''),
            'request_owner': os.environ.get('AGENT_QUERY_REQUEST_OWNER', ''),
            'rc_details': os.environ.get('AGENT_QUERY_RC_DETAILS', ''),
            'missing_notes': os.environ.get('AGENT_QUERY_MISSING_NOTES', ''),
            'integration_test': os.environ.get('AGENT_QUERY_INTEGRATION_TEST', ''),
            'broadcast': os.environ.get('AGENT_QUERY_BROADCAST', '')
        }
        
        
        # Channel mappings - load from JSON string in environment
        channel_mappings_str = os.environ.get('CHANNEL_MAPPINGS', '{}')
        try:
            self.channel_mappings = json.loads(channel_mappings_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CHANNEL_MAPPINGS JSON: {e}")
            # Fallback to empty dict
            self.channel_mappings = {}
        
        # Regex patterns
        self.patterns = {
            'channel_id': os.environ.get('CHANNEL_ID_PATTERN', r'\b(C[A-Z0-9]{10,})\b'),
            'channel_ref': os.environ.get('CHANNEL_REF_PATTERN', r'#([a-z0-9-]+)'),
            'at_symbol': os.environ.get('AT_SYMBOL_PATTERN', r'@([a-zA-Z0-9_-]+)'),
            'mention': os.environ.get('MENTION_PATTERN', r'<@[A-Z0-9]+>'),
            'heading': os.environ.get('HEADING_PATTERN', r'^#{1,6}\s+(.+)$'),
            'bold': os.environ.get('BOLD_PATTERN', r'\*\*(.+?)\*\*'),
            'italic': os.environ.get('ITALIC_PATTERN', r'(?<!\*)\*([^*]+?)\*(?!\*)'),
            'link': os.environ.get('LINK_PATTERN', r'\[([^\]]+)\]\(([^)]+)\)'),
            'bullet': os.environ.get('BULLET_PATTERN', r'^[\*\-]\s+'),
            'channel_mention': os.environ.get('CHANNEL_MENTION_PATTERN', r'(?<!<)#([a-zA-Z0-9_-]+)(?!>)'),
            'version': os.environ.get('VERSION_PATTERN', r'version\s+(\d+\.\d+\.\d+)')
        }
                
        # Logging and preview settings
        self.log_query_preview_length = int(os.environ.get('LOG_QUERY_PREVIEW_LENGTH', 100))
        self.log_context_preview_length = int(os.environ.get('LOG_CONTEXT_PREVIEW_LENGTH', 200))
        self.log_history_preview_length = int(os.environ.get('LOG_HISTORY_PREVIEW_LENGTH', 50))
        self.log_max_history_entries = int(os.environ.get('LOG_MAX_HISTORY_ENTRIES', 2))
        
        # Phase 2: Multi-agent configuration (for individual use or testing)
        self.oscar_knowledge_agent_id = os.environ.get('OSCAR_KNOWLEDGE_AGENT_ID')
        self.oscar_knowledge_agent_alias_id = os.environ.get('OSCAR_KNOWLEDGE_AGENT_ALIAS_ID')
        self.oscar_metrics_agent_id = os.environ.get('OSCAR_METRICS_AGENT_ID')
        self.oscar_metrics_agent_alias_id = os.environ.get('OSCAR_METRICS_AGENT_ALIAS_ID')
        self.oscar_build_agent_id = os.environ.get('OSCAR_BUILD_AGENT_ID')
        self.oscar_build_agent_alias_id = os.environ.get('OSCAR_BUILD_AGENT_ALIAS_ID')
        self.oscar_test_agent_id = os.environ.get('OSCAR_TEST_AGENT_ID')
        self.oscar_test_agent_alias_id = os.environ.get('OSCAR_TEST_AGENT_ALIAS_ID')

    def _load_env_from_secrets(self) -> None:
        """Load environment variables from AWS Secrets Manager."""
        try:
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            
            # Get the .env content from secrets manager
            response = client.get_secret_value(SecretId='oscar-central-env')
            env_content = response['SecretString']
            
            # Load the .env content into environment variables
            config_stream = StringIO(env_content)
            load_dotenv(stream=config_stream, override=True)
            
            logger.info("Successfully loaded environment variables from AWS Secrets Manager")
            
        except Exception as e:
            logger.error(f"Error loading environment from secrets manager: {e}")
            logger.warning("Falling back to local environment variables")
            # Continue with local environment variables if secrets manager fails
    

    def get_slack_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get Slack credentials from environment variables.
        
        Returns:
            A tuple containing (slack_bot_token, slack_signing_secret)
        """
        return self.slack_bot_token, self.slack_signing_secret

class _ConfigProxy:
    """Proxy that caches config per lambda execution."""
    def __init__(self):
        self._cached_config = None
        self.aws_request_id = None
        self._lambda_request_id = None
    
    def set_request_id(self, request_id: str) -> None:
        """Set the AWS Lambda request ID."""
        self.aws_request_id = request_id
    
    def __getattr__(self, name):
        # If no config cached yet or request ID changed, create fresh config
        if self._cached_config is None or (self.aws_request_id and self._lambda_request_id != self.aws_request_id):
            self._cached_config = Config(validate_required=False)
            self._lambda_request_id = self.aws_request_id
        
        return getattr(self._cached_config, name)

# Global configuration proxy
config = _ConfigProxy()