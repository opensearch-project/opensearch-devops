#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Authorization utilities for Slack Handler.
"""

import logging
from slack_handler.constants import AUTHORIZED_MESSAGE_SENDERS

logger = logging.getLogger(__name__)


class AuthorizationManager:
    """Manages user authorization for various Slack operations."""
    
    @staticmethod
    def is_message_sending_request(query: str) -> bool:
        """Check if the query is requesting automated message sending.
        
        Args:
            query: The user's query
            
        Returns:
            True if this is a message sending request
        """
        query_lower = query.lower()
        message_keywords = [
            'send message', 'send notification', 'send alert', 'post message',
            'notify channel', 'send to channel', 'message channel',
            'message', 'release notes message', 'ping people', 'ping'
        ]
        
        return any(keyword in query_lower for keyword in message_keywords)
    
    @staticmethod
    def is_user_authorized_for_messaging(user_id: str) -> bool:
        """Check if user is authorized for automated message sending.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            True if user is authorized
        """
        return user_id in AUTHORIZED_MESSAGE_SENDERS