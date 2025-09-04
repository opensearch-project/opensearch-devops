#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Slack client management for Communication Handler.
"""

import logging
import os
from config import config
from typing import Any, Dict

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from message_formatter import MessageFormatter

logger = logging.getLogger(__name__)


class SlackClientManager:
    """Manages Slack client interactions."""
    
    def __init__(self) -> None:
        """Initialize Slack client."""
        slack_token = config.slack_bot_token
        self.client = WebClient(token=slack_token) if slack_token else None
        self.message_formatter = MessageFormatter()
    
    def send_message(self, channel: str, message: str) -> Dict[str, Any]:
        """Send message to Slack channel.
        
        Args:
            channel: Target channel ID
            message: Message content (will be automatically formatted for Slack)
            
        Returns:
            Dictionary with success status and response data
        """
        if not self.client:
            return {'success': False, 'error': 'Slack client not initialized - missing SLACK_BOT_TOKEN'}
        
        try:
            # Automatically format the message for Slack before sending
            # This handles markdown conversion and cleans up formatting issues
            logger.debug(f"Formatting message for Slack (channel: {channel}, length: {len(message)})")
            formatted_message = self.message_formatter.format_markdown_to_slack_mrkdwn(message)
            formatted_message = self.message_formatter.convert_at_symbols_to_slack_pings(formatted_message)
            
            logger.info(f"Sending message to channel {channel}")
            response = self.client.chat_postMessage(
                channel=channel,
                text=formatted_message,
                unfurl_links=False,
                unfurl_media=False
            )
            logger.info(f"Slack API response: ok={response.get('ok')}, ts={response.get('ts')}")
            
            return {
                'success': True,
                'message_ts': response.get('ts'),
                'channel': channel,
                'response': response
            }
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response}")
            return {
                'success': False,
                'error': f'Slack API error: {e.response.get("error", str(e))}'
            }
        except Exception as e:
            logger.error(f"Unexpected error sending Slack message: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }