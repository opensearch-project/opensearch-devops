#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Tests for the slack_handler module.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import time

# Add the parent directory to sys.path to import the modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Mock the config before importing slack_handler
with patch('config.config') as mock_config:
    # Set properties on the mocked config singleton
    mock_config.enable_dm = False
    mock_config.context_summary_length = 500
    
    # Import the SlackHandler class directly
    from slack_handler import SlackHandler

class TestSlackHandler(unittest.TestCase):
    """Test cases for the SlackHandler class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock app, storage, and knowledge base
        self.mock_app = MagicMock()
        self.mock_storage = MagicMock()
        self.mock_knowledge_base = MagicMock()
        
        # Set up mock app client
        self.mock_app.client = MagicMock()
        self.mock_app.client.auth_test.return_value = {"user_id": "test-bot-id"}
        
        # Create handler instance
        self.handler = SlackHandler(
            self.mock_app,
            self.mock_storage,
            self.mock_knowledge_base
        )
    
    def test_is_duplicate_event(self):
        """Test duplicate event detection."""
        # Set up mock
        self.mock_storage.has_seen_event.return_value = True
        
        event = {
            'event_ts': '1234567890.123456'
        }
        
        result = self.handler._is_duplicate_event(event)
        
        # Verify result
        self.assertTrue(result)
        
        # Verify storage check
        self.mock_storage.has_seen_event.assert_called_once_with('1234567890.123456')
    
    def test_extract_query(self):
        """Test query extraction from message text."""
        # Test with mention
        text_with_mention = "<@U12345> Hello, how are you?"
        result = self.handler._extract_query(text_with_mention)
        self.assertEqual(result, "Hello, how are you?")
        
        # Test without mention
        text_without_mention = "Hello, how are you?"
        result = self.handler._extract_query(text_without_mention)
        self.assertEqual(result, "Hello, how are you?")
        
        # Test with multiple mentions
        text_with_multiple_mentions = "<@U12345> Hello <@U67890>, how are you?"
        result = self.handler._extract_query(text_with_multiple_mentions)
        self.assertEqual(result, "Hello , how are you?")
    
    def test_manage_reactions(self):
        """Test managing reactions on messages."""
        # Test adding a reaction
        self.handler._manage_reactions("C12345", "1234567890.123456", add_reaction="thumbsup")
        self.mock_app.client.reactions_add.assert_called_once_with(
            channel="C12345",
            timestamp="1234567890.123456",
            name="thumbsup"
        )
        
        # Reset mock
        self.mock_app.client.reset_mock()
        
        # Test removing a reaction
        self.handler._manage_reactions("C12345", "1234567890.123456", remove_reaction="thumbsdown")
        self.mock_app.client.reactions_remove.assert_called_once_with(
            channel="C12345",
            timestamp="1234567890.123456",
            name="thumbsdown"
        )
        
        # Reset mock
        self.mock_app.client.reset_mock()
        
        # Test both adding and removing reactions
        self.handler._manage_reactions("C12345", "1234567890.123456", 
                                      add_reaction="thumbsup", 
                                      remove_reaction="thumbsdown")
        self.mock_app.client.reactions_remove.assert_called_once_with(
            channel="C12345",
            timestamp="1234567890.123456",
            name="thumbsdown"
        )
        self.mock_app.client.reactions_add.assert_called_once_with(
            channel="C12345",
            timestamp="1234567890.123456",
            name="thumbsup"
        )
    
    def test_update_context(self):
        """Test updating conversation context."""
        # Set up test data
        thread_key = "C12345_1234567890.123456"
        query = "What is OpenSearch?"
        response = "OpenSearch is a distributed search and analytics engine."
        session_id = "old-session-id"
        new_session_id = "new-session-id"
        
        # Mock storage.get_context to return None (no existing context)
        self.mock_storage.get_context.return_value = None
        
        # Call the method
        context = self.handler._update_context(thread_key, query, response, session_id, new_session_id)
        
        # Verify the context structure
        self.assertEqual(context["session_id"], new_session_id)
        self.assertEqual(len(context["history"]), 1)
        self.assertEqual(context["history"][0]["query"], query)
        self.assertEqual(context["history"][0]["response"], response)
        self.assertIn("timestamp", context["history"][0])
        
        # Verify storage.store_context was called
        self.mock_storage.store_context.assert_called_once_with(thread_key, context)
        
        # Reset mocks
        self.mock_storage.reset_mock()
        
        # Test with existing context
        existing_context = {
            "session_id": session_id,
            "history": [
                {
                    "query": "Previous query",
                    "response": "Previous response",
                    "timestamp": int(time.time()) - 100
                }
            ],
            "summary": "Previous summary"
        }
        self.mock_storage.get_context.return_value = existing_context
        
        # Call the method again
        updated_context = self.handler._update_context(thread_key, query, response, session_id, new_session_id)
        
        # Verify the context was updated correctly
        self.assertEqual(updated_context["session_id"], new_session_id)
        self.assertEqual(len(updated_context["history"]), 2)
        self.assertEqual(updated_context["history"][1]["query"], query)
        self.assertEqual(updated_context["history"][1]["response"], response)
        
        # Verify storage.store_context was called with updated context
        self.mock_storage.store_context.assert_called_once_with(thread_key, updated_context)
    
    def test_process_message(self):
        """Test message processing workflow."""
        # Set up test data
        channel = "C12345"
        thread_ts = "1234567890.123456"
        user_id = "U12345"
        text = "<@U67890> Hello, how are you?"
        say = MagicMock()
        message_ts = "1234567890.123457"
        
        # Mock knowledge base response
        self.mock_knowledge_base.query.return_value = ("I'm doing well, thank you!", "session-123")
        
        # Mock storage.get_context
        self.mock_storage.get_context.return_value = {
            "session_id": "old-session",
            "history": [],
            "summary": ""
        }
        
        # Mock time.time to return consistent values for testing
        with patch('time.time') as mock_time:
            # Set up time.time to return increasing values
            # We need enough values for all the time.time calls in the method
            mock_time.return_value = 1000  # Use a constant value instead of side_effect
            
            # Call the method
            self.handler._process_message(channel, thread_ts, user_id, text, say, message_ts)
        
        # Verify reactions were managed correctly
        self.mock_app.client.reactions_add.assert_any_call(
            channel=channel,
            timestamp=message_ts,
            name="thinking_face"
        )
        
        self.mock_app.client.reactions_add.assert_any_call(
            channel=channel,
            timestamp=message_ts,
            name="white_check_mark"
        )
        
        # Verify knowledge base was queried
        self.mock_knowledge_base.query.assert_called_once()
        query_args = self.mock_knowledge_base.query.call_args[0]
        self.assertEqual(query_args[0], "Hello, how are you?")  # Extracted query
        
        # Verify response was sent
        say.assert_called_once_with(text="I'm doing well, thank you!", thread_ts=thread_ts)
        
        # Verify context was updated
        self.mock_storage.store_context.assert_called_once()

    def test_handle_app_mention(self):
        """Test handling of app_mention events."""
        # Set up test data
        event = {
            "channel": "C12345",
            "ts": "1234567890.123456",
            "user": "U12345",
            "text": "<@U67890> Hello, how are you?",
            "thread_ts": None
        }
        say = MagicMock()
        
        # Mock _process_message
        with patch.object(self.handler, '_process_message') as mock_process:
            # Call the method
            self.handler.handle_app_mention(event, say)
            
            # Verify _process_message was called with correct arguments
            mock_process.assert_called_once_with(
                "C12345",  # channel
                "1234567890.123456",  # thread_ts (same as ts since thread_ts is None)
                "U12345",  # user_id
                "<@U67890> Hello, how are you?",  # text
                say,  # say function
                message_ts="1234567890.123456"  # message_ts (same as ts)
            )
    
    def test_handle_message(self):
        """Test handling of direct message events."""
        # Set up test data for DM
        message = {
            "channel_type": "im",
            "channel": "D12345",
            "ts": "1234567890.123456",
            "user": "U12345",
            "text": "Hello, how are you?",
            "thread_ts": None
        }
        say = MagicMock()
        
        # Mock _process_message
        with patch.object(self.handler, '_process_message') as mock_process:
            # Call the method
            self.handler.handle_message(message, say)
            
            # Verify _process_message was called with correct arguments
            mock_process.assert_called_once_with(
                "D12345",  # channel
                "1234567890.123456",  # thread_ts (same as ts since thread_ts is None)
                "U12345",  # user_id
                "Hello, how are you?",  # text
                say,  # say function
                message_ts="1234567890.123456"  # message_ts (same as ts)
            )
        
        # Reset mock
        mock_process.reset_mock()
        
        # Test with non-DM message (should not process)
        non_dm_message = {
            "channel_type": "channel",
            "channel": "C12345",
            "ts": "1234567890.123456",
            "user": "U12345",
            "text": "Hello, how are you?",
            "thread_ts": None
        }
        
        # Call the method with non-DM message
        self.handler.handle_message(non_dm_message, say)
        
        # Verify _process_message was NOT called
        mock_process.assert_not_called()
    
    def test_register_handlers(self):
        """Test registration of event handlers."""
        # Ensure config.enable_dm is False for this test
        with patch('config.config.enable_dm', False):
            # Call the method
            result = self.handler.register_handlers()
            
            # Verify app.event was called for app_mention
            self.mock_app.event.assert_called_with("app_mention")
            
            # Verify app.message was NOT called (since enable_dm is False)
            self.mock_app.message.assert_not_called()
            
            # Verify the app was returned
            self.assertEqual(result, self.mock_app)
        
        # Test with enable_dm=True
        with patch('config.config.enable_dm', True):
            # Reset mock
            self.mock_app.reset_mock()
            
            # Create new handler with mocked config
            handler = SlackHandler(self.mock_app, self.mock_storage, self.mock_knowledge_base)
            
            # Call register_handlers
            handler.register_handlers()
            
            # Verify app.event was called for app_mention
            self.mock_app.event.assert_called_with("app_mention")
            
            # Verify app.message was called (since enable_dm is True)
            self.mock_app.message.assert_called_once()

if __name__ == '__main__':
    unittest.main()