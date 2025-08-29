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
        
        Only converts @ symbols that are not already in Slack ping format.
        This prevents double-formatting of pings that are already properly formatted.
        
        Args:
            message: Message content with @ symbols
            
        Returns:
            Message with Slack ping format
        """
        logger.debug(f"Converting @ symbols to Slack pings (length: {len(message)})")
        # Only convert @ symbols that are NOT already inside < > brackets
        # This prevents converting <@username> to <<@username>>
        result = re.sub(r'(?<!<)@([a-zA-Z0-9_-]+)(?![^<]*>)', r'<@\1>', message)
        return result
    
    @staticmethod
    def format_markdown_to_slack_mrkdwn(message: str) -> str:
        """Convert standard Markdown to Slack's mrkdwn format.
        
        Based on Slack's mrkdwn specification:
        - **bold** becomes *bold*
        - *italic* becomes _italic_
        - # Heading becomes *Heading*
        - [text](url) becomes <url|text>
        - * list item becomes • list item
        
        Args:
            message: Message content in standard Markdown format
            
        Returns:
            Message formatted for Slack's mrkdwn syntax
        """
        try:
            logger.debug(f"Converting markdown to Slack mrkdwn (length: {len(message)})")
            
            # Start with the original message
            formatted = message
            
            # Step 1: Convert bold text (**text**) to Slack format (*text*) FIRST
            # This must be done before italic conversion to avoid conflicts
            # Handle both **text** and __text__ patterns
            formatted = re.sub(r'\*\*(.+?)\*\*', r'*\1*', formatted)
            formatted = re.sub(r'__(.+?)__', r'*\1*', formatted)
            
            # Step 2: Convert headings (# Heading, ## Heading, etc.) to bold text (*Heading*)
            # This handles all heading levels and removes the # symbols
            formatted = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', formatted, flags=re.MULTILINE)
            
            # Step 3: Convert italic text (*text*) to Slack format (_text_)
            # We skip automatic italic conversion to avoid conflicts with bold formatting.
            # Users can use _text_ directly for italics if needed.
            
            # Step 4: Convert links [text](url) to Slack format <url|text>
            formatted = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', formatted)
            
            # Step 5: Convert bullet points (* item or - item) to bullet symbol (• item)
            formatted = re.sub(r'^[\*\-]\s+', r'• ', formatted, flags=re.MULTILINE)
            
            # Step 6: Convert #channel mentions to Slack format <#channel>
            # Only convert if not already in Slack format
            formatted = re.sub(r'(?<!<)#([a-zA-Z0-9_-]+)(?!>)', r'<#\1>', formatted)
            
            # Step 7: Clean up any formatting artifacts
            # Remove any double asterisks that might have been created
            formatted = re.sub(r'\*\*+', r'*', formatted)
            # Remove any double underscores that might have been created  
            formatted = re.sub(r'__+', r'_', formatted)
            
            logger.debug(f"Markdown conversion completed (original: {len(message)}, final: {len(formatted)})")
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting message to Slack mrkdwn: {e}", exc_info=True)
            logger.error(f"Original message that failed: {message[:500]}...")
            return message  # Return original message if formatting fails