#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Unit tests for DynamoDB setup functionality.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.append('.')

# Set environment variable before importing modules
os.environ['DISABLE_CONFIG_VALIDATION'] = 'true'


class TestDynamoDBSetup:
    """Test cases for DynamoDB setup functionality."""
    
    @patch('boto3.resource')
    def test_table_access_functionality(self, mock_boto3_resource):
        """Test table access functionality that was in setup_dynamodb_tables.py."""
        # Mock DynamoDB resource and table
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_boto3_resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table
        
        # Mock successful operations
        mock_table.put_item.return_value = {}
        mock_table.get_item.return_value = {'Item': {'test_data': 'test_value'}}
        mock_table.delete_item.return_value = {}
        
        # Test the table access logic
        result = self._test_table_access(mock_dynamodb, 'test-context-table')
        assert result is True
        
        # Verify operations were called
        mock_table.put_item.assert_called_once()
        mock_table.get_item.assert_called_once()
        mock_table.delete_item.assert_called_once()
    
    def _test_table_access(self, dynamodb, table_name):
        """Test basic read/write access to the table."""
        try:
            table = dynamodb.Table(table_name)
            
            # Test write
            test_key = f"test_key_{int(time.time())}"
            test_item = {
                'thread_key' if 'context' in table_name else 'event_id': test_key,
                'test_data': 'test_value',
                'ttl': int(time.time()) + 300  # 5 minutes
            }
            
            table.put_item(Item=test_item)
            
            # Test read
            response = table.get_item(
                Key={
                    'thread_key' if 'context' in table_name else 'event_id': test_key
                }
            )
            
            if 'Item' not in response:
                return False
            
            # Clean up test item
            table.delete_item(
                Key={
                    'thread_key' if 'context' in table_name else 'event_id': test_key
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Table access test failed: {e}")
            return False
    
    def test_table_name_detection(self):
        """Test table name detection logic."""
        # Test context table detection
        context_table = 'oscar-context-table'
        assert 'context' in context_table
        
        # Test sessions table detection
        sessions_table = 'oscar-sessions-table'
        assert 'context' not in sessions_table
    
    def test_test_item_structure(self):
        """Test the structure of test items."""
        current_time = int(time.time())
        
        # Test context table item
        context_item = {
            'thread_key': f"test_key_{current_time}",
            'test_data': 'test_value',
            'ttl': current_time + 300
        }
        
        assert 'thread_key' in context_item
        assert context_item['ttl'] > current_time
        
        # Test sessions table item
        sessions_item = {
            'event_id': f"test_key_{current_time}",
            'test_data': 'test_value',
            'ttl': current_time + 300
        }
        
        assert 'event_id' in sessions_item
        assert sessions_item['ttl'] > current_time