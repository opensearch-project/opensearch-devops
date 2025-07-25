#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Tests for the storage module.
"""

import unittest
import time
from unittest.mock import patch, MagicMock
import os
import sys

# Add the parent directory to sys.path to import the modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Set required environment variables for testing
os.environ.setdefault('KNOWLEDGE_BASE_ID', 'test-kb-id')
os.environ.setdefault('SLACK_BOT_TOKEN', 'test-bot-token')
os.environ.setdefault('SLACK_SIGNING_SECRET', 'test-signing-secret')

# Import the storage classes directly
from storage import DynamoDBStorage, StorageInterface
from config import config


class InMemoryStorage(StorageInterface):
    """In-memory implementation of storage interface for testing."""
    
    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self.contexts: dict[str, dict[str, any]] = {}
        self.seen_events: dict[str, dict[str, any]] = {}
        self.dedup_ttl = 300  # Default TTL for testing
        self.context_ttl = 3600  # Default TTL for testing
    
    def store_context(self, thread_key: str, context: dict[str, any]) -> bool:
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
    
    def get_context(self, thread_key: str) -> dict[str, any] | None:
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
            return self.contexts[thread_key]['context']
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
        return True


class TestInMemoryStorage(unittest.TestCase):
    """Test cases for the InMemoryStorage class."""
    
    def setUp(self):
        """Set up test environment."""
        self.storage = InMemoryStorage()
    
    def test_store_and_get_context(self):
        """Test storing and retrieving context."""
        # Create test context
        context = {
            'session_id': 'test-session',
            'history': [{'query': 'test query', 'response': 'test response'}],
            'summary': 'test summary'
        }
        
        # Store context
        result = self.storage.store_context('thread-1', context)
        self.assertTrue(result)
        
        # Retrieve context
        retrieved = self.storage.get_context('thread-1')
        self.assertEqual(retrieved, context)
        
        # Non-existent thread should return None
        self.assertIsNone(self.storage.get_context('thread-2'))
    
    def test_context_expiration(self):
        """Test that context expires after TTL."""
        context = {'test': 'data'}
        
        # Set a very short TTL for testing
        self.storage.context_ttl = 1
        
        # Store context
        self.storage.store_context('thread-1', context)
        
        # Should be retrievable immediately
        self.assertEqual(self.storage.get_context('thread-1'), context)
        
        # Wait for expiration
        time.sleep(2)
        
        # Should be None after expiration
        self.assertIsNone(self.storage.get_context('thread-1'))
    
    def test_event_deduplication(self):
        """Test event deduplication functionality."""
        event_id = 'test-event-123'
        
        # Event should not be seen initially
        self.assertFalse(self.storage.has_seen_event(event_id))
        
        # Mark event as seen
        result = self.storage.mark_event_seen(event_id)
        self.assertTrue(result)
        
        # Event should now be seen
        self.assertTrue(self.storage.has_seen_event(event_id))
        
        # Different event should not be seen
        self.assertFalse(self.storage.has_seen_event('different-event'))
    
    def test_event_expiration(self):
        """Test that seen events expire after TTL."""
        event_id = 'test-event-456'
        
        # Set a very short TTL for testing
        self.storage.dedup_ttl = 1
        
        # Mark event as seen
        self.storage.mark_event_seen(event_id)
        
        # Should be seen immediately
        self.assertTrue(self.storage.has_seen_event(event_id))
        
        # Wait for expiration
        time.sleep(2)
        
        # Should not be seen after expiration
        self.assertFalse(self.storage.has_seen_event(event_id))

if __name__ == '__main__':
    unittest.main()