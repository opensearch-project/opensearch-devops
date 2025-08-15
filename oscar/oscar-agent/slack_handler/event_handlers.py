#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Event handlers for Slack Handler.
"""

import logging
from typing import Any, Callable, Dict

from slack_handler.constants import CHANNEL_ALLOW_LIST
from slack_handler.authorization import AuthorizationManager

logger = logging.getLogger(__name__)


class EventHandlers:
    """Handles different types of Slack events."""
    
    def __init__(self, message_processor) -> None:
        """Initialize with message processor.
        
        Args:
            message_processor: MessageProcessor instance
        """
        self.message_processor = message_processor
        self.auth_manager = AuthorizationManager()
    
    def handle_app_mention(self, event: Dict[str, Any], say: Callable) -> None:
        """Handle app_mention events.
        
        Args:
            event: Slack event data
            say: Function to send a message to the channel
        """
        # Extract message details
        channel = event.get("channel")
        if channel not in CHANNEL_ALLOW_LIST:
            logger.info(f"Channel {channel} not in allow list, ignoring event")
            return
        thread_ts = event.get("thread_ts") or event.get("ts")
        user_id = event.get("user")
        text = event.get("text")
        event_ts = event.get("ts")  # Use ts for the specific message, not thread_ts
        
        logger.info(f"Processing app_mention event: channel={channel}, ts={event_ts}, thread_ts={thread_ts}")
        
        # Process the message
        self.message_processor.process_message(channel, thread_ts, user_id, text, say, message_ts=event_ts)
    
    def handle_message(self, message: Dict[str, Any], say: Callable) -> None:
        """Handle direct message events.
        
        Args:
            message: Slack message data
            say: Function to send a message to the channel
        """
        # Only process DM messages
        channel_type = message.get("channel_type")
        if channel_type != "im":
            return
        
        # Extract message details
        channel = message.get("channel")
        thread_ts = message.get("thread_ts") or message.get("ts")
        user_id = message.get("user")
        text = message.get("text")
        event_ts = message.get("ts")  # Use ts for the specific message
        
        # Check if user is authorized for DM access
        if not self.auth_manager.is_user_authorized_for_messaging(user_id):
            logger.warning(f"Unauthorized DM attempt by user {user_id}")
            say(text="❌ You are not authorized to use OSCAR via direct messages.")
            return
        
        logger.info(f"Processing DM message event: channel={channel}, ts={event_ts}, thread_ts={thread_ts}")
        
        # Process the message
        self.message_processor.process_message(channel, thread_ts, user_id, text, say, message_ts=event_ts)