#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Slack messaging utilities for Slack Handler.
"""

import logging
from typing import Any, Dict
from slack_sdk.errors import SlackApiError

from config import config
from .message_formatter import MessageFormatter

logger = logging.getLogger(__name__)


class SlackMessaging:
    """Handles Slack message sending functionality."""
    
    def __init__(self, client, storage) -> None:
        """Initialize with Slack client and storage.
        
        Args:
            client: Slack client instance
            storage: Storage instance
        """
        self.client = client
        self.storage = storage
        self.message_formatter = MessageFormatter()
    
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
            if channel not in config.channel_allow_list:
                return {
                    "success": False,
                    "error": f"Channel {channel} not in allow list"
                }
            
            # Automatically format the message for Slack before sending
            # This handles markdown conversion and cleans up formatting issues
            logger.debug(f"Formatting message for Slack (length: {len(message)})")
            formatted_message = self.message_formatter.format_markdown_to_slack_mrkdwn(message)
            formatted_message = self.message_formatter.convert_at_symbols_to_slack_pings(formatted_message)
            
            # Send message
            response = self.client.chat_postMessage(
                channel=channel,
                text=formatted_message,
                unfurl_links=False,
                unfurl_media=False
            )
            
            # Store context for the bot message to enable follow-up conversations
            if response and 'ts' in response:
                self.storage.store_bot_message_context(channel, response['ts'], formatted_message)
            
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