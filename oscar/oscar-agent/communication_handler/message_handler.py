#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Message handling for Communication Handler.
"""

import logging
from typing import Any, Dict

from communication_handler.channel_utils import ChannelUtils
from communication_handler.context_storage import ContextStorage
from communication_handler.message_formatter import MessageFormatter
from communication_handler.response_builder import ResponseBuilder
from communication_handler.slack_client import SlackClientManager

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles message sending and formatting operations."""
    
    def __init__(self) -> None:
        """Initialize message handler components."""
        self.slack_client = SlackClientManager()
        self.context_storage = ContextStorage()
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
            logger.info(f"Message content provided: {bool(message_content)}")
            
            # Use provided message content (agent should provide complete message)
            if message_content:
                # Convert @username to <@username> for Slack pings
                processed_message = self.message_formatter.convert_at_symbols_to_slack_pings(message_content)
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
            result = self.slack_client.send_message(target_channel, processed_message)
            
            if result.get('success'):
                # Store context for the sent message to enable follow-up conversations
                if result.get('message_ts'):
                    self.context_storage.store_cross_channel_context(
                        target_channel, 
                        result.get('message_ts'), 
                        query, 
                        processed_message
                    )
                
                logger.info(f"Message sending completed successfully: {result}")
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
            logger.error(f"Query was: '{query}'")
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