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

logger = logging.getLogger(__name__)


class SlackClientManager:
    """Manages Slack client interactions."""
    
    def __init__(self) -> None:
        """Initialize Slack client."""
        slack_token = os.environ.get('SLACK_BOT_TOKEN')
        self.client = WebClient(token=slack_token) if slack_token else None
    
    def send_message(self, channel: str, message: str) -> Dict[str, Any]:
        """Send message to Slack channel.
        
        Args:
            channel: Target channel ID
            message: Message content
            
        Returns:
            Dictionary with success status and response data
        """
        if not self.client:
            return {'success': False, 'error': 'Slack client not initialized - missing SLACK_BOT_TOKEN'}
        
        try:
            logger.info(f"Sending message to channel {channel}: {message[:config.message_preview_length]}...")
            response = self.client.chat_postMessage(
                channel=channel,
                text=message,
                unfurl_links=False,
                unfurl_media=False
            )
            logger.info(f"Slack API response: {response.get('ok')}, ts: {response.get('ts')}")
            
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
            logger.error(f"Unexpected error sending Slack message: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }