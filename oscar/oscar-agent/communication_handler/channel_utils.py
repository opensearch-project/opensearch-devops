#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Channel utilities for Communication Handler.
"""

import logging
import re
from typing import Optional
from config import config

logger = logging.getLogger(__name__)


class ChannelUtils:
    """Utilities for channel extraction and validation."""
    
    @staticmethod
    def extract_channel_from_query(query: str) -> Optional[str]:
        """Extract channel from user query.
        
        Args:
            query: User's natural language query
            
        Returns:
            Channel ID if found, None otherwise
        """
        # Channel ID pattern - direct channel ID in query
        channel_id_match = re.search(config.patterns['channel_id'], query)
        if channel_id_match:
            channel_id = channel_id_match.group(1)
            return channel_id if channel_id in config.channel_allow_list else None
        
        # Channel reference patterns (#channel-name)
        channel_ref_match = re.search(config.patterns['channel_ref'], query.lower())
        if channel_ref_match:
            channel_name = channel_ref_match.group(1)
            # Use configured channel mappings
            return config.channel_mappings.get(channel_name)
        
        # Text-based channel mentions using configured mappings
        # Check if any channel name from mappings appears in the query text
        query_lower = query.lower()
        for channel_name, channel_id in config.channel_mappings.items():
            # Check if channel name (with or without hashtag) appears in query
            if channel_name in query_lower:
                return channel_id
        
        return None
    
    @staticmethod
    def validate_channel(channel: str) -> bool:
        """Validate if channel is in allow list.
        
        Args:
            channel: Channel ID to validate
            
        Returns:
            True if channel is allowed, False otherwise
        """
        return channel in config.channel_allow_list