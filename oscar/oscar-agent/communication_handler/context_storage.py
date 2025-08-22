#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Context storage for Communication Handler.
"""

import logging
import os
import time
from typing import Any, Dict

import boto3
from config import config

logger = logging.getLogger(__name__)


class ContextStorage:
    """Manages context storage for cross-channel messages."""
    
    def __init__(self) -> None:
        """Initialize DynamoDB connection."""
        self.dynamodb = boto3.resource('dynamodb', region_name=config.region)
        self.context_table_name = config.context_table_name
        self.context_table = self.dynamodb.Table(self.context_table_name)
    
    def store_cross_channel_context(self, channel: str, message_ts: str, original_query: str, sent_message: str) -> None:
        """Store context for a message sent to a different channel to enable follow-up conversations.
        
        Args:
            channel: Target channel where the message was sent
            message_ts: Timestamp of the sent message
            original_query: Original user query that triggered the message (will be redacted for privacy)
            sent_message: The actual message that was sent
        """
        try:
            thread_key = f"{channel}_{message_ts}"
            logger.info(f"🌐 CROSS_CHANNEL_CONTEXT: Starting storage for thread_key='{thread_key}'")
            logger.info(f"🌐 CROSS_CHANNEL_CONTEXT: channel='{channel}', message_ts='{message_ts}', sent_message_len={len(sent_message)}")
            
            # Redact the original query for privacy/security reasons
            # The original query could contain sensitive info or reveal who made the request
            redacted_query = "[Automated message sent from another channel - original request details redacted for the user's privacy]"
            
            # Create context for the sent message
            context = {
                "session_id": None,  # New conversation thread
                "history": [
                    {
                        "query": redacted_query,
                        "response": sent_message,
                        "timestamp": int(time.time())
                    }
                ]
            }
            
            logger.info(f"🌐 CROSS_CHANNEL_CONTEXT: Created context with {len(context['history'])} history entries")
            
            # Store with TTL
            current_time = int(time.time())
            expiration = current_time + config.context_ttl
            item = {
                'thread_key': thread_key,
                'context': context,
                'ttl': expiration,
                'updated_at': current_time
            }
            
            logger.info(f"🗄️ CROSS_CHANNEL_CONTEXT: DynamoDB item - thread_key='{thread_key}', ttl={expiration}, updated_at={current_time}")
            logger.info(f"🗄️ CROSS_CHANNEL_CONTEXT: Table name='{self.context_table_name}'")
            
            self.context_table.put_item(Item=item)
            logger.info(f"✅ CROSS_CHANNEL_CONTEXT: Successfully stored cross-channel context for thread {thread_key} in channel {channel}")
            
        except Exception as e:
            logger.error(f"❌ CROSS_CHANNEL_CONTEXT: Error storing cross-channel context for {channel}_{message_ts}: {e}", exc_info=True)