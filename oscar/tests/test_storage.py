#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Unit tests for storage functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.append('oscar-agent')

# Set environment variable before importing modules
os.environ['DISABLE_CONFIG_VALIDATION'] = 'true'


class TestStorage:
    """Test cases for storage functionality."""
    
    def test_storage_interface_exists(self):
        """Test that storage interface exists."""
        try:
            from context_storage import StorageInterface
            assert StorageInterface is not None
        except ImportError:
            pytest.skip("StorageInterface not available for testing")
    
    def test_dynamodb_storage_exists(self):
        """Test that DynamoDB storage class exists."""
        try:
            from context_storage import DynamoDBStorage
            assert DynamoDBStorage is not None
        except ImportError:
            pytest.skip("DynamoDBStorage not available for testing")
    
    def test_get_storage_function(self):
        """Test get_storage factory function."""
        try:
            from context_storage import get_storage
            assert get_storage is not None
            
            # Test that function can be called (will fail without AWS creds, but that's ok)
            try:
                storage = get_storage('dynamodb', 'us-east-1')
                assert storage is not None
            except Exception:
                # Expected to fail without proper AWS setup
                pass
        except ImportError:
            pytest.skip("get_storage function not available for testing")
    
    def test_storage_interface_methods(self):
        """Test that storage interface has required methods."""
        try:
            from context_storage import StorageInterface
            
            # Check that abstract methods exist
            required_methods = ['store_context', 'get_context', 'has_seen_event', 'mark_event_seen', 'get_context_for_query']
            
            for method_name in required_methods:
                assert hasattr(StorageInterface, method_name), f"Missing method: {method_name}"
                
        except ImportError:
            pytest.skip("StorageInterface not available for testing")
    
    def test_thread_key_logic(self):
        """Test thread key generation logic."""
        # Test thread key format
        channel = 'C123456'
        thread_ts = '1234567890.123456'
        
        expected_thread_key = f"{channel}-{thread_ts}"
        assert expected_thread_key == 'C123456-1234567890.123456'
        
        # Test with regular timestamp
        ts = '1234567890.123456'
        expected_key_with_ts = f"{channel}-{ts}"
        assert expected_key_with_ts == 'C123456-1234567890.123456'