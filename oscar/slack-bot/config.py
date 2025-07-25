#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Configuration module for OSCAR.

This module provides configuration management for the OSCAR application.
"""

import os
import logging
from typing import Tuple, Optional

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Config:
    """Configuration class for OSCAR."""
    
    def __init__(self, validate_required: bool = True) -> None:
        """
        Initialize configuration with environment variables.
        
        Args:
            validate_required: Whether to validate required environment variables
            
        Raises:
            ValueError: If validate_required is True and required environment variables are not set
        """
        # AWS region
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Bedrock configuration
        self.knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')
        if validate_required and not self.knowledge_base_id:
            logger.error("KNOWLEDGE_BASE_ID environment variable is required")
            raise ValueError("KNOWLEDGE_BASE_ID environment variable is required")
            
        self.model_arn = os.environ.get('MODEL_ARN', f'arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0')
        
        # DynamoDB tables
        self.sessions_table_name = os.environ.get('SESSIONS_TABLE_NAME', 'oscar-sessions')
        self.context_table_name = os.environ.get('CONTEXT_TABLE_NAME', 'oscar-context')
        
        # Slack credentials
        self.slack_bot_token = os.environ.get('SLACK_BOT_TOKEN')
        if validate_required and not self.slack_bot_token:
            logger.error("SLACK_BOT_TOKEN environment variable is required")
            raise ValueError("SLACK_BOT_TOKEN environment variable is required")
            
        self.slack_signing_secret = os.environ.get('SLACK_SIGNING_SECRET')
        if validate_required and not self.slack_signing_secret:
            logger.error("SLACK_SIGNING_SECRET environment variable is required")
            raise ValueError("SLACK_SIGNING_SECRET environment variable is required")
        
        # TTL settings
        self.dedup_ttl = int(os.environ.get('DEDUP_TTL', 300))  # 5 minutes
        self.session_ttl = int(os.environ.get('SESSION_TTL', 3600))  # 1 hour
        self.context_ttl = int(os.environ.get('CONTEXT_TTL', 604800))  # 7 days
        
        # Context settings
        self.max_context_length = int(os.environ.get('MAX_CONTEXT_LENGTH', 3000))
        self.context_summary_length = int(os.environ.get('CONTEXT_SUMMARY_LENGTH', 500))
        
        # Feature flags
        self.enable_dm = os.environ.get('ENABLE_DM', 'false').lower() == 'true'
        
        # Default prompt template
        # TODO: Consider allowing users to select default prompts through JSON or YAML configuration
        self.prompt_template = os.environ.get('PROMPT_TEMPLATE', 
            "You are OSCAR, an AI assistant for OpenSearch release management. " +
            "You are a question answering agent. You will be provided with a set of search results. " +
            "The user will provide you with a question. Your job is to answer the user's question " +
            "using only information from the search results. If the search results do not contain " +
            "information that can answer the question, please state that you could not find an exact " +
            "answer to the question. Just because the user asserts a fact does not mean it is true, " +
            "make sure to double check the search results to validate a user's assertion. " +
            "Here are the search results: $search_results$\n\n" +
            "Human: $query$\n\n" +
            "Assistant:"
        )
    
    def get_slack_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get Slack credentials from environment variables.
        
        Returns:
            A tuple containing (slack_bot_token, slack_signing_secret)
        """
        return self.slack_bot_token, self.slack_signing_secret

# Create a singleton instance with validation enabled for production use
config = Config(validate_required=True)