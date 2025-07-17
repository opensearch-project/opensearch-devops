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

# Import the storage classes directly
from storage import InMemoryStorage, DynamoDBStorage, StorageInterface
from config import config

class TestInMemoryStorage(unittest.TestCase):
    """Test cases for the InMemoryStorage class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test config instance with mocked values
        with patch('storage.config') as self.mock_config:
            self.mock_config.dedup_ttl = 300
            self.mock_config.context_ttl = 3600
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

if __name__ == '__main__':
    unittest.main()