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
        # Channel ID pattern
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
        query_lower = query.lower()
        if 'riley-needs-to-lock-in' in query_lower:
            return config.channel_mappings.get('riley-needs-to-lock-in')
        elif '3-2-0' in query_lower or '3.2.0' in query_lower or 'release channel' in query_lower:
            return config.channel_mappings.get('opensearch-release-manager')
        elif 'build channel' in query_lower:
            return config.channel_mappings.get('private-oscar-test')
        elif 'test channel' in query_lower:
            return config.channel_mappings.get('riley-needs-to-lock-in')
        elif 'dev channel' in query_lower:
            return config.channel_mappings.get('opensearch-3-2-0-release')
        
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