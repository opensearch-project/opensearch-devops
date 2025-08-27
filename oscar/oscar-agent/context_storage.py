#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Consolidated Storage Management for OSCAR Agent.

Provides unified storage for conversation context with DynamoDB backend.
"""

import logging
logger = logging.getLogger(__name__)
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import boto3
from config import config


class StorageInterface(ABC):
    """Abstract storage interface."""
    
    @abstractmethod
    def store_context(self, thread_key: str, context: Dict[str, Any]) -> bool:
        """Store conversation context for a thread."""
        pass
    
    @abstractmethod
    def get_context(self, thread_key: str) -> Optional[Dict[str, Any]]:
        """Get conversation context for a thread."""
        pass
    
    @abstractmethod
    def get_context_for_query(self, thread_key: str) -> str:
        """Get conversation context formatted for prepending to a query."""
        pass
    
    @abstractmethod
    def update_context(self, thread_key: str, query: str, response: str, 
                      session_id: Optional[str], new_session_id: Optional[str]) -> Dict[str, Any]:
        """Update the conversation context with the new query and response."""
        pass
    
    @abstractmethod
    def store_bot_message_context(self, channel: str, thread_ts: str, bot_message: str, 
                                 session_id: Optional[str] = None, user_query: str = None) -> None:
        """Store context for bot-initiated messages to enable follow-up conversations."""
        pass
    
    @abstractmethod
    def store_cross_channel_context(self, channel: str, message_ts: str, 
                                   original_query: str, sent_message: str) -> None:
        """Store context for a message sent to a different channel to enable follow-up conversations."""
        pass

class StorageManager(StorageInterface):
    """Consolidated DynamoDB storage manager."""
    
    def __init__(self, region: Optional[str] = None) -> None:
        """Initialize DynamoDB storage with configuration."""
        self.region = region or config.region
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.context_table = self.dynamodb.Table(config.context_table_name)
        self.context_ttl = config.context_ttl
        self.context_table_name = config.context_table_name

    
    def store_context(self, thread_key: str, context: Dict[str, Any]) -> bool:
        """Store conversation context in DynamoDB."""
        try:
            if not isinstance(context, dict):
                logger.error(f"Invalid context type for {thread_key}: {type(context)}")
                return False
            
            # Ensure required fields
            if "history" not in context:
                context["history"] = []
            if "session_id" not in context:
                context["session_id"] = None
            
            # Store with TTL
            current_time = int(time.time())
            expiration = current_time + self.context_ttl
            item = {
                'thread_key': thread_key,
                'context': context,
                'ttl': expiration,
                'updated_at': current_time
            }
            
            self.context_table.put_item(Item=item)
            logger.info(f"Stored context for thread {thread_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing context for {thread_key}: {e}")
            return False
    
    def get_context(self, thread_key: str) -> Optional[Dict[str, Any]]:
        """Get conversation context from DynamoDB."""
        try:
            response = self.context_table.get_item(
                Key={'thread_key': thread_key}
            )

            if 'Item' in response:
                item = response['Item']
                
                # Check TTL
                if 'ttl' in item:
                    ttl = item['ttl']
                    current_time = int(time.time())
                    if ttl < current_time:
                        return None
                
                context = item.get('context')
                if context:                    
                    # Validate context structure
                    if not isinstance(context, dict):
                        return None
                                        
                    # Ensure required fields exist
                    if "history" not in context:
                        context["history"] = []
                    if "session_id" not in context:
                        context["session_id"] = None
                    
                    return context
                else:
                    return None
            else:
                return None
            
        except Exception as e:
            logger.error(f"Error retrieving context for {thread_key}: {e}")
            return None
    
    def get_context_for_query(self, thread_key: str) -> str:
        """Get conversation context formatted for prepending to a query."""
        try:
            context = self.get_context(thread_key)
            if not context:
                return ""
            
            history = context.get("history", [])
            if not history:
                return ""
            
            context_lines = [""]
            for entry in history:
                query = entry.get("query", "")
                response = entry.get("response", "")
                context_lines.extend([f"User: {query}", f"Assistant: {response}", ""])
            
            return "\n".join(context_lines)
            
        except Exception as e:
            logger.error(f"Error generating context for query (thread {thread_key}): {e}")
            return ""
    
    def update_context(self, thread_key: str, query: str, response: str, 
                      session_id: Optional[str], new_session_id: Optional[str]) -> Dict[str, Any]:
        """Update the conversation context with the new query and response."""
        try:            
            # Get existing context or create a new one
            context = self.get_context(thread_key)
            if not context:
                context = {
                    "session_id": new_session_id or session_id,
                    "history": []
                }
            
            # Update session ID - prefer new_session_id, but keep existing if new one is None
            if new_session_id:
                context["session_id"] = new_session_id
            elif session_id and not context.get("session_id"):
                context["session_id"] = session_id
            
            # Ensure history exists
            if "history" not in context:
                context["history"] = []            
            
            # Append to history
            new_entry = {
                "query": query,
                "response": response,
                "timestamp": int(time.time())
            }
            context["history"].append(new_entry)
            
            # Store updated context
            self.store_context(thread_key, context)
            return context
            
        except Exception as e:
            logger.error(f"Error updating context for thread {thread_key}: {e}")
            # Return a minimal context to prevent complete failure
            return {
                "session_id": new_session_id or session_id,
                "history": [{"query": query, "response": response, "timestamp": int(time.time())}]
            }
    
    def store_bot_message_context(self, channel: str, thread_ts: str, bot_message: str, 
                                 session_id: Optional[str] = None, user_query: str = None) -> None:
        """Store context for bot-initiated messages to enable follow-up conversations."""
        thread_key = f"{channel}_{thread_ts}"
        
        # Create context for bot-initiated message
        context = {
            "session_id": session_id,
            "history": []
        }
        
        # If there was a user query (for slash commands), add it to history
        if user_query:
            context["history"].append({
                "query": user_query,
                "response": bot_message,
                "timestamp": int(time.time())
            })
        else:
            # For pure bot-initiated messages, create a synthetic entry
            context["history"].append({
                "query": "[Bot initiated conversation]",
                "response": bot_message,
                "timestamp": int(time.time())
            })
        
        # Store the context
        self.store_context(thread_key, context)
        logger.info(f"Stored bot message context for thread {thread_ts}")
    
    def store_cross_channel_context(self, channel: str, message_ts: str, 
                                   original_query: str, sent_message: str) -> None:
        """Store context for a message sent to a different channel to enable follow-up conversations."""
        try:
            thread_key = f"{channel}_{message_ts}"
            
            context = {
                "session_id": None,
                "history": [{
                    "query": "[Automated message sent from another channel - original request details redacted for the user's privacy]",
                    "response": sent_message,
                    "timestamp": int(time.time())
                }]
            }
            
            current_time = int(time.time())
            expiration = current_time + config.context_ttl
            item = {
                'thread_key': thread_key,
                'context': context,
                'ttl': expiration,
                'updated_at': current_time
            }
            
            self.context_table.put_item(Item=item)
            logger.info(f"Stored cross-channel context for {thread_key}")
            
        except Exception as e:
            logger.error(f"Error storing cross-channel context for {channel}_{message_ts}: {e}")

# Backward compatibility
DynamoDBStorage = StorageManager

def get_storage(storage_type: str = 'dynamodb', region: Optional[str] = None) -> StorageInterface:
    """Get storage implementation based on type."""
    return StorageManager(region)