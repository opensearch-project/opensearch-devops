#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Message formatting utilities for Communication Handler.
"""

import logging
import re
from config import config
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Handles message formatting and template processing."""
    
    @staticmethod
    def convert_at_symbols_to_slack_pings(message: str) -> str:
        """Convert @username to <@username> for Slack pings.
        
        Args:
            message: Message content with @ symbols
            
        Returns:
            Message with Slack ping format
        """
        return re.sub(config.patterns['at_symbol'], r'<@\1>', message)
    
    @staticmethod
    def format_markdown_to_slack_mrkdwn(message: str) -> str:
        """Convert standard Markdown to Slack's mrkdwn format.
        
        Args:
            message: Message content in standard Markdown format
            
        Returns:
            Message formatted for Slack's mrkdwn syntax
        """
        try:
            # Start with the original message
            formatted = message
            
            # Convert headings (# Heading) to bold text (*Heading*)
            # Handle multiple levels of headings
            formatted = re.sub(config.patterns['heading'], r'*\1*', formatted, flags=re.MULTILINE)
            
            # Convert italic text (*text* or _text_) to Slack format (_text_) FIRST
            # This must be done before bold conversion to avoid conflicts
            formatted = re.sub(config.patterns['italic'], r'_\1_', formatted)
            formatted = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'_\1_', formatted)
            
            # Convert bold text (**text** or __text__) to Slack format (*text*)
            formatted = re.sub(config.patterns['bold'], r'*\1*', formatted)
            formatted = re.sub(r'__(.+?)__', r'*\1*', formatted)
            
            # Convert links [text](url) to Slack format <url|text>
            formatted = re.sub(config.patterns['link'], r'<\2|\1>', formatted)
            
            # Convert bullet points (* item or - item) to consistent format
            formatted = re.sub(config.patterns['bullet'], r'• ', formatted, flags=re.MULTILINE)
            
            # Note: @username mentions are handled by convert_at_symbols_to_slack_pings()
            # to avoid double conversion, we don't convert them here
            
            # Convert #channel mentions to Slack format <#channel>
            # Only convert if not already in Slack format
            formatted = re.sub(config.patterns['channel_mention'], r'<#\1>', formatted)
            
            # Clean up any double formatting that might have occurred
            formatted = re.sub(config.patterns['bold'], r'*\1*', formatted)  # Fix double bold
            formatted = re.sub(r'__([^_]+)__', r'_\1_', formatted)      # Fix double italic
            
            logger.info(f"Successfully formatted message from {len(message)} to {len(formatted)} characters")
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting message to Slack mrkdwn: {e}")
            return message  # Return original message if formatting fails