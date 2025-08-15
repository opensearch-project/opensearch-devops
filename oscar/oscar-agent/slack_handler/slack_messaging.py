#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Slack messaging utilities for Slack Handler.
"""

import logging
from typing import Any, Dict
from slack_sdk.errors import SlackApiError

from slack_handler.constants import CHANNEL_ALLOW_LIST

logger = logging.getLogger(__name__)


class SlackMessaging:
    """Handles Slack message sending functionality."""
    
    def __init__(self, client, context_manager) -> None:
        """Initialize with Slack client and context manager.
        
        Args:
            client: Slack client instance
            context_manager: ContextManager instance
        """
        self.client = client
        self.context_manager = context_manager
    
    def send_slack_message(self, channel: str, message: str) -> Dict[str, Any]:
        """Send a message to a Slack channel.
        
        This method is called by the supervisor agent's action group function.
        
        Args:
            channel: Target Slack channel ID or name
            message: Message content to send
            
        Returns:
            Dictionary with send result
        """
        try:
            # Validate channel is in allow list
            if channel not in CHANNEL_ALLOW_LIST:
                return {
                    "success": False,
                    "error": f"Channel {channel} not in allow list"
                }
            
            # Send message
            response = self.client.chat_postMessage(
                channel=channel,
                text=message,
                unfurl_links=False,
                unfurl_media=False
            )
            
            # Store context for the bot message to enable follow-up conversations
            if response and 'ts' in response:
                self.context_manager.store_bot_message_context(channel, response['ts'], message)
            
            logger.info(f"Successfully sent automated message to channel {channel}")
            return {
                "success": True,
                "channel": channel,
                "message_ts": response["ts"]
            }
            
        except SlackApiError as e:
            error_msg = f"Slack API error: {e.response['error']}"
            logger.error(f"Failed to send message to {channel}: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to send message to {channel}: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }