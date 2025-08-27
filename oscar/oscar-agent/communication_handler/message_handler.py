#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Message handling for Communication Handler.
"""

import logging
logger = logging.getLogger(__name__)
from typing import Any, Dict

from channel_utils import ChannelUtils
from context_storage import get_storage
from message_formatter import MessageFormatter
from response_builder import ResponseBuilder
from slack_client import SlackClientManager

class MessageHandler:
    """Handles message sending and formatting operations."""
    
    def __init__(self) -> None:
        """Initialize message handler components."""
        self.slack_client = SlackClientManager()
        try:
            self.storage = get_storage()
        except Exception as e:
            logger.error(f"Failed to create storage instance: {e}")
            self.storage = None
        self.channel_utils = ChannelUtils()
        self.message_formatter = MessageFormatter()
        self.response_builder = ResponseBuilder()
    
    def handle_send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the send_message action.
        
        Args:
            params: Parameters from the agent request
            
        Returns:
            Response for the agent
        """
        try:
            # Extract parameters
            query = params.get('query', '')
            message_content = params.get('message_content', '')
            target_channel = params.get('target_channel', '')
            
            logger.info(f"Processing message request: query='{query}', channel='{target_channel}'")
            logger.debug(f"Message content length: {len(message_content) if message_content else 0}")
            
            # Use provided message content (agent should provide complete message)
            if message_content:
                # Message formatting is now handled automatically in SlackClient.send_message()
                processed_message = message_content
                logger.debug(f"Using provided message content (length: {len(processed_message)})")
            else:
                logger.error("No message content provided - agent should fill template with metrics")
                return self.response_builder.create_error_response(
                    'send_automated_message',
                    'No message content provided. Agent must provide complete message with metrics data.'
                )
            
            # Extract target channel from query if not provided
            if not target_channel:
                target_channel = self.channel_utils.extract_channel_from_query(query)
                if not target_channel:
                    logger.error(f"Failed to extract channel from query: '{query}'")
                    return self.response_builder.create_error_response(
                        'send_automated_message',
                        f'Could not determine target channel from query: "{query}". Please specify channel using #channel-name or channel ID.'
                    )
            
            # Validate channel is in allow list
            if not self.channel_utils.validate_channel(target_channel):
                return self.response_builder.create_error_response(
                    'send_automated_message',
                    f'Channel {target_channel} is not in the allowed channels list'
                )
            
            # Send message to Slack
            logger.debug(f"Sending message to channel '{target_channel}' (length: {len(processed_message)})")
            result = self.slack_client.send_message(target_channel, processed_message)
            
            if result.get('success'):
                # Store context for the sent message to enable follow-up conversations
                if result.get('message_ts') and self.storage:
                    try:
                        self.storage.store_cross_channel_context(
                            target_channel, 
                            result.get('message_ts'), 
                            query, 
                            processed_message
                        )
                    except Exception as e:
                        logger.error(f"Failed to store cross-channel context: {e}")
                
                logger.info(f"Message sent successfully to channel {target_channel}")
                return self.response_builder.create_success_response(
                    'send_automated_message',
                    f"✅ Message sent successfully to channel {target_channel}"
                )
            else:
                logger.error(f"Message sending failed for query '{query}': {result.get('error')}")
                return self.response_builder.create_error_response(
                    'send_automated_message',
                    result.get('error', 'Failed to send message')
                )
                
        except Exception as e:
            logger.error(f"Error in handle_send_message: {e}", exc_info=True)
            return self.response_builder.create_error_response(
                'send_automated_message',
                f'Error processing message: {str(e)}'
            )
    
    def handle_format_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the format_message_for_slack action.
        
        Args:
            params: Parameters from the agent request
            
        Returns:
            Response for the agent with formatted message
        """
        try:
            # Extract parameters
            message_content = params.get('message_content', '')
            
            logger.info(f"Processing message formatting request for content length: {len(message_content)}")
            
            if not message_content:
                return self.response_builder.create_error_response(
                    'format_message_for_slack',
                    'No message content provided to format'
                )
            
            # Format the message for Slack
            formatted_message = self.message_formatter.format_markdown_to_slack_mrkdwn(message_content)
            
            logger.info(f"Message formatting completed successfully")
            
            return self.response_builder.create_success_response(
                'format_message_for_slack',
                formatted_message
            )
            
        except Exception as e:
            logger.error(f"Error in handle_format_message: {e}", exc_info=True)
            return self.response_builder.create_error_response(
                'format_message_for_slack',
                f'Error formatting message: {str(e)}'
            )