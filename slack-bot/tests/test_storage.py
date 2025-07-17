"""
Tests for the storage module.
"""

import unittest
from unittest.mock import patch, MagicMock
from oscar.storage import InMemoryStorage, DynamoDBStorage

class TestInMemoryStorage(unittest.TestCase):
    """Test cases for the InMemoryStorage class."""
    
    def setUp(self):
        """Set up test environment."""
        self.storage = InMemoryStorage()
    
    def test_is_duplicate_event(self):
        """Test duplicate event detection."""
        # First time should not be a duplicate
        self.assertFalse(self.storage.is_duplicate_event('test-event-1'))
        
        # Second time should be a duplicate
        self.assertTrue(self.storage.is_duplicate_event('test-event-1'))
        
        # Different event ID should not be a duplicate
        self.assertFalse(self.storage.is_duplicate_event('test-event-2'))
    
    def test_session_context_storage_and_retrieval(self):
        """Test storing and retrieving session context."""
        # Initially no session or context
        session_id, context = self.storage.get_session_context('thread-1', 'channel-1')
        self.assertIsNone(session_id)
        self.assertIsNone(context)
        
        # Store session ID
        self.storage.store_session_context('thread-1', 'channel-1', 'session-1', 'test query', 'test response')
        
        # Should retrieve session ID
        session_id, context = self.storage.get_session_context('thread-1', 'channel-1')
        self.assertEqual(session_id, 'session-1')
        self.assertIsNone(context)
        
        # Different thread should have no session
        session_id, context = self.storage.get_session_context('thread-2', 'channel-1')
        self.assertIsNone(session_id)
        self.assertIsNone(context)
    
    def test_context_summary_storage_and_retrieval(self):
        """Test storing and retrieving context summary."""
        # Store context without session ID
        self.storage.store_session_context('thread-2', 'channel-1', None, 'test query', 'test response')
        
        # Should retrieve context summary
        session_id, context = self.storage.get_session_context('thread-2', 'channel-1')
        self.assertIsNone(session_id)
        self.assertIsNotNone(context)
        self.assertIn('test query', context)
        self.assertIn('test response', context)
    
    def test_context_appending(self):
        """Test appending to existing context."""
        # Store initial context
        self.storage.store_session_context('thread-3', 'channel-1', None, 'query 1', 'response 1')
        
        # Append to context
        self.storage.store_session_context('thread-3', 'channel-1', None, 'query 2', 'response 2')
        
        # Should contain both interactions
        _, context = self.storage.get_session_context('thread-3', 'channel-1')
        self.assertIn('query 1', context)
        self.assertIn('response 1', context)
        self.assertIn('query 2', context)
        self.assertIn('response 2', context)

class TestDynamoDBStorage(unittest.TestCase):
    """Test cases for the DynamoDBStorage class."""
    
    @patch('boto3.resource')
    def setUp(self, mock_boto_resource):
        """Set up test environment with mocked DynamoDB."""
        # Set up mock DynamoDB tables
        self.mock_sessions_table = MagicMock()
        self.mock_context_table = MagicMock()
        
        # Set up mock DynamoDB resource
        mock_dynamodb = MagicMock()
        mock_boto_resource.return_value = mock_dynamodb
        mock_dynamodb.Table.side_effect = [self.mock_sessions_table, self.mock_context_table]
        
        # Create storage instance
        self.storage = DynamoDBStorage(region='us-west-2')
    
    def test_is_duplicate_event(self):
        """Test duplicate event detection with DynamoDB."""
        # Set up mock for non-duplicate case
        self.mock_sessions_table.put_item.return_value = {}
        
        # Should not be a duplicate
        self.assertFalse(self.storage.is_duplicate_event('test-event-1'))
        
        # Verify put_item was called correctly
        self.mock_sessions_table.put_item.assert_called_once()
        args, kwargs = self.mock_sessions_table.put_item.call_args
        self.assertIn('Item', kwargs)
        self.assertIn('ConditionExpression', kwargs)
        self.assertEqual(kwargs['Item']['session_key'], 'dedup_test-event-1')
        
        # Set up mock for duplicate case
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'ConditionalCheckFailedException'}}
        self.mock_sessions_table.put_item.side_effect = ClientError(error_response, 'PutItem')
        
        # Should be a duplicate
        self.assertTrue(self.storage.is_duplicate_event('test-event-1'))
    
    def test_get_session_context_with_active_session(self):
        """Test retrieving active session from DynamoDB."""
        # Set up mock for active session
        self.mock_sessions_table.get_item.return_value = {
            'Item': {
                'session_key': 'channel-1_thread-1',
                'session_id': 'session-1'
            }
        }
        
        # Should retrieve session ID
        session_id, context = self.storage.get_session_context('thread-1', 'channel-1')
        self.assertEqual(session_id, 'session-1')
        self.assertIsNone(context)
        
        # Verify get_item was called correctly
        self.mock_sessions_table.get_item.assert_called_once_with(
            Key={'session_key': 'channel-1_thread-1'}
        )
    
    def test_get_session_context_with_stored_context(self):
        """Test retrieving context summary from DynamoDB."""
        # Set up mock for no active session
        self.mock_sessions_table.get_item.return_value = {}
        
        # Set up mock for stored context
        self.mock_context_table.get_item.return_value = {
            'Item': {
                'thread_key': 'channel-1_thread-2',
                'context_summary': 'Q: test query\nA: test response'
            }
        }
        
        # Should retrieve context summary
        session_id, context = self.storage.get_session_context('thread-2', 'channel-1')
        self.assertIsNone(session_id)
        self.assertEqual(context, 'Q: test query\nA: test response')
        
        # Verify get_item was called correctly
        self.mock_context_table.get_item.assert_called_once_with(
            Key={'thread_key': 'channel-1_thread-2'}
        )

if __name__ == '__main__':
    unittest.main()