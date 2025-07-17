"""
Storage module for OSCAR.

This module provides classes for storing and retrieving session and context data.
"""

import time
import logging
import boto3
from botocore.exceptions import ClientError
from abc import ABC, abstractmethod
from .config import config

# Configure logging
logger = logging.getLogger(__name__)

class StorageInterface(ABC):
    """Abstract base class for storage implementations."""
    
    @abstractmethod
    def get_session_context(self, thread_ts, channel):
        """Get session ID and context for thread."""
        pass
    
    @abstractmethod
    def store_session_context(self, thread_ts, channel, session_id, query, response_text):
        """Store both session ID and context summary."""
        pass
    
    @abstractmethod
    def is_duplicate_event(self, event_id):
        """Check if an event is a duplicate."""
        pass

class DynamoDBStorage(StorageInterface):
    """DynamoDB implementation of storage interface."""
    
    def __init__(self, region=None):
        """Initialize DynamoDB storage."""
        self.region = region or config.region
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.sessions_table = self.dynamodb.Table(config.sessions_table_name)
        self.context_table = self.dynamodb.Table(config.context_table_name)
    
    def get_session_context(self, thread_ts, channel):
        """Get session ID and context for thread."""
        if not thread_ts:
            return None, None
        
        thread_key = f"{channel}_{thread_ts}"
        
        # Try to get active Bedrock session (1 hour)
        try:
            response = self.sessions_table.get_item(Key={'session_key': thread_key})
            if 'Item' in response:
                return response['Item']['session_id'], None
        except Exception as e:
            logger.error(f"Error retrieving session: {e}")
        
        # If no active session, get stored context (48 hours)
        try:
            response = self.context_table.get_item(Key={'thread_key': thread_key})
            if 'Item' in response:
                return None, response['Item']['context_summary']
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
        
        return None, None
    
    def store_session_context(self, thread_ts, channel, session_id, query, response_text):
        """Store both session ID and context summary."""
        if not thread_ts:
            return
        
        thread_key = f"{channel}_{thread_ts}"
        current_time = int(time.time())
        
        # Store active session (1 hour TTL)
        if session_id:
            try:
                self.sessions_table.put_item(
                    Item={
                        'session_key': thread_key,
                        'session_id': session_id,
                        'ttl': current_time + config.session_ttl
                    }
                )
            except Exception as e:
                logger.error(f"Error storing session: {e}")
        
        # Store/update context summary (48 hour TTL)
        try:
            existing = self.context_table.get_item(Key={'thread_key': thread_key})
            if 'Item' in existing:
                # Append to existing context
                context = existing['Item']['context_summary'] + f"\n\nQ: {query}\nA: {response_text[:config.context_summary_length]}..."
            else:
                # New context
                context = f"Q: {query}\nA: {response_text[:config.context_summary_length]}..."
            
            # Keep context under 4KB (DynamoDB item limit)
            if len(context) > config.max_context_length:
                context = context[-config.max_context_length:]  # Keep recent context
            
            self.context_table.put_item(
                Item={
                    'thread_key': thread_key,
                    'context_summary': context,
                    'ttl': current_time + config.context_ttl
                }
            )
        except Exception as e:
            logger.error(f"Error storing context: {e}")
    
    def is_duplicate_event(self, event_id):
        """Check for duplicates using DynamoDB atomic operations."""
        try:
            self.sessions_table.put_item(
                Item={
                    'session_key': f"dedup_{event_id}",
                    'processed': True,
                    'ttl': int(time.time()) + config.dedup_ttl
                },
                ConditionExpression='attribute_not_exists(session_key)'
            )
            return False  # Not duplicate
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return True  # Duplicate found
            logger.error(f"Error checking for duplicate event: {e}")
            raise

class InMemoryStorage(StorageInterface):
    """In-memory implementation of storage interface for testing and development."""
    
    def __init__(self):
        """Initialize in-memory storage."""
        self.sessions = {}
        self.contexts = {}
        self.dedup = {}
    
    def get_session_context(self, thread_ts, channel):
        """Get session ID and context for thread."""
        if not thread_ts:
            return None, None
        
        thread_key = f"{channel}_{thread_ts}"
        
        # Try to get active session
        if thread_key in self.sessions:
            return self.sessions[thread_key], None
        
        # If no active session, get stored context
        if thread_key in self.contexts:
            return None, self.contexts[thread_key]
        
        return None, None
    
    def store_session_context(self, thread_ts, channel, session_id, query, response_text):
        """Store both session ID and context summary."""
        if not thread_ts:
            return
        
        thread_key = f"{channel}_{thread_ts}"
        
        # Store active session
        if session_id:
            self.sessions[thread_key] = session_id
        
        # Store/update context summary
        if thread_key in self.contexts:
            # Append to existing context
            context = self.contexts[thread_key] + f"\n\nQ: {query}\nA: {response_text[:config.context_summary_length]}..."
        else:
            # New context
            context = f"Q: {query}\nA: {response_text[:config.context_summary_length]}..."
        
        # Keep context under limit
        if len(context) > config.max_context_length:
            context = context[-config.max_context_length:]  # Keep recent context
        
        self.contexts[thread_key] = context
    
    def is_duplicate_event(self, event_id):
        """Check if an event is a duplicate."""
        if event_id in self.dedup:
            return True
        
        self.dedup[event_id] = True
        return False

# Factory function to create the appropriate storage implementation
def get_storage(storage_type='dynamodb', region=None):
    """Get storage implementation based on type."""
    if storage_type == 'memory':
        return InMemoryStorage()
    return DynamoDBStorage(region)