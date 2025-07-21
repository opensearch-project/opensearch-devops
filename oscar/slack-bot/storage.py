#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Storage module for OSCAR.

This module provides storage implementations for session and context data.
"""

import time
import logging
from typing import Dict, Any, Optional, Union
import boto3
from abc import ABC, abstractmethod

from config import config

# Configure logging
logger = logging.getLogger(__name__)

class StorageInterface(ABC):
    """Abstract base class for storage implementations."""
    
    @abstractmethod
    def store_context(self, thread_key: str, context: Dict[str, Any]) -> bool:
        """
        Store conversation context for a thread.
        
        Args:
            thread_key: Unique identifier for the conversation thread
            context: Dictionary containing conversation context data
            
        Returns:
            True if storage was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_context(self, thread_key: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation context for a thread.
        
        Args:
            thread_key: Unique identifier for the conversation thread
            
        Returns:
            Dictionary containing conversation context data, or None if not found
        """
        pass
    
    @abstractmethod
    def has_seen_event(self, event_id: str) -> bool:
        """
        Check if an event has been seen before.
        
        Args:
            event_id: Unique identifier for the event
            
        Returns:
            True if the event has been seen before, False otherwise
        """
        pass
    
    @abstractmethod
    def mark_event_seen(self, event_id: str) -> bool:
        """
        Mark an event as seen.
        
        Args:
            event_id: Unique identifier for the event
            
        Returns:
            True if the event was successfully marked as seen, False otherwise
        """
        pass

class DynamoDBStorage(StorageInterface):
    """DynamoDB implementation of storage interface."""
    
    def __init__(self, region: Optional[str] = None) -> None:
        """
        Initialize DynamoDB storage.
        
        Args:
            region: AWS region for DynamoDB service, defaults to config value if None
        """
        self.region = region or config.region
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.sessions_table = self.dynamodb.Table(config.sessions_table_name)
        self.context_table = self.dynamodb.Table(config.context_table_name)
        self.dedup_ttl = config.dedup_ttl
        self.context_ttl = config.context_ttl
    
    def store_context(self, thread_key: str, context: Dict[str, Any]) -> bool:
        """
        Store conversation context in DynamoDB.
        
        Args:
            thread_key: Unique identifier for the conversation thread
            context: Dictionary containing conversation context data
            
        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Ensure context size is within limits
            if len(str(context)) > config.max_context_length:
                logger.warning(f"Context for {thread_key} exceeds max length, truncating history")
                # Keep only the most recent history entries
                while len(str(context)) > config.max_context_length and len(context.get("history", [])) > 1:
                    context["history"].pop(0)
            
            # Store with TTL
            expiration = int(time.time()) + self.context_ttl
            self.context_table.put_item(
                Item={
                    'thread_key': thread_key,
                    'context': context,
                    'ttl': expiration
                }
            )
            logger.info(f"Stored context for thread {thread_key}")
            return True
        except Exception as e:
            logger.error(f"Error storing context: {e}")
            return False
    
    def get_context(self, thread_key: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation context from DynamoDB.
        
        Args:
            thread_key: Unique identifier for the conversation thread
            
        Returns:
            Dictionary containing conversation context data, or None if not found
        """
        try:
            response = self.context_table.get_item(
                Key={'thread_key': thread_key}
            )
            if 'Item' in response:
                logger.info(f"Retrieved context for thread {thread_key}")
                return response['Item'].get('context')
            logger.info(f"No context found for thread {thread_key}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return None
    
    def has_seen_event(self, event_id: str) -> bool:
        """
        Check if an event has been seen before in DynamoDB.
        
        Args:
            event_id: Unique identifier for the event
            
        Returns:
            True if the event has been seen before, False otherwise
        """
        try:
            response = self.sessions_table.get_item(
                Key={'event_id': event_id}
            )
            
            if 'Item' in response:
                # Check if the item has expired (TTL might not have been processed yet)
                if 'ttl' in response['Item']:
                    ttl = response['Item']['ttl']
                    current_time = int(time.time())
                    if ttl < current_time:
                        logger.info(f"Event {event_id} found but TTL expired, treating as new")
                        return False
                
                logger.info(f"Event {event_id} has been seen before")
                return True
            
            logger.info(f"Event {event_id} has not been seen before")
            return False
        except Exception as e:
            logger.error(f"Error checking event: {e}")
            return False
    
    def mark_event_seen(self, event_id: str) -> bool:
        """
        Mark an event as seen in DynamoDB.
        
        Args:
            event_id: Unique identifier for the event
            
        Returns:
            True if the event was successfully marked as seen, False otherwise
        """
        try:
            # Store event with TTL
            expiration = int(time.time()) + self.dedup_ttl
            current_time = int(time.time())
            
            self.sessions_table.put_item(
                Item={
                    'event_id': event_id,
                    'timestamp': current_time,
                    'ttl': expiration
                }
            )
            logger.info(f"Marked event {event_id} as seen")
            return True
        except Exception as e:
            logger.error(f"Error marking event: {e}")
            return False

class InMemoryStorage(StorageInterface):
    """In-memory implementation of storage interface for testing."""
    
    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self.contexts: Dict[str, Dict[str, Union[Dict[str, Any], int]]] = {}
        self.seen_events: Dict[str, Dict[str, Any]] = {}
        self.dedup_ttl = config.dedup_ttl
        self.context_ttl = config.context_ttl
    
    def store_context(self, thread_key: str, context: Dict[str, Any]) -> bool:
        """
        Store conversation context in memory.
        
        Args:
            thread_key: Unique identifier for the conversation thread
            context: Dictionary containing conversation context data
            
        Returns:
            True if storage was successful
        """
        self.contexts[thread_key] = {
            'context': context,
            'expiration': int(time.time()) + self.context_ttl
        }
        return True
    
    def get_context(self, thread_key: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation context from memory.
        
        Args:
            thread_key: Unique identifier for the conversation thread
            
        Returns:
            Dictionary containing conversation context data, or None if not found or expired
        """
        if thread_key in self.contexts:
            # Check if expired
            if self.contexts[thread_key]['expiration'] < int(time.time()):
                del self.contexts[thread_key]
                return None
            return self.contexts[thread_key]['context']  # type: ignore
        return None
    
    def has_seen_event(self, event_id: str) -> bool:
        """
        Check if an event has been seen before in memory.
        
        Args:
            event_id: Unique identifier for the event
            
        Returns:
            True if the event has been seen before and not expired, False otherwise
        """
        if event_id in self.seen_events:
            # Check if expired
            if self.seen_events[event_id]['ttl'] < int(time.time()):
                del self.seen_events[event_id]
                return False
            return True
        return False
    
    def mark_event_seen(self, event_id: str) -> bool:
        """
        Mark an event as seen in memory.
        
        Args:
            event_id: Unique identifier for the event
            
        Returns:
            True if the event was successfully marked as seen, False otherwise
        """
        current_time = int(time.time())
        expiration = current_time + self.dedup_ttl
        
        self.seen_events[event_id] = {
            'timestamp': current_time,
            'ttl': expiration
        }
        logger.info(f"Marked event {event_id} as seen")
        return True

def get_storage(storage_type: str = 'dynamodb', region: Optional[str] = None) -> StorageInterface:
    """
    Get storage implementation based on type.
    
    Args:
        storage_type: Type of storage to create ('dynamodb' or 'memory')
        region: AWS region for DynamoDB service, defaults to config value if None
        
    Returns:
        An implementation of StorageInterface
    """
    if storage_type == 'memory':
        return InMemoryStorage()
    return DynamoDBStorage(region)