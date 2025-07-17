"""
Tests for the slack_handler module.
"""

import unittest
from unittest.mock import patch, MagicMock, call
from oscar.slack_handler import SlackHandler

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
    
    def test_create_event_id(self):
        """Test creating event ID."""
        event = {
            'channel': 'C12345',
            'user': 'U12345',
            'ts': '1234567890.123456',
            'text': 'test message'
        }
        
        event_id = self.handler.create_event_id(event)
        
        # Verify event ID format
        self.assertIn('C12345', event_id)
        self.assertIn('U12345', event_id)
        self.assertIn('1234567890.123456', event_id)
        self.assertTrue(len(event_id) > 30)  # Should be reasonably long
    
    def test_has_bot_responded_true(self):
        """Test detection of bot response."""
        # Set up mock response with bot reply
        self.mock_app.client.conversations_replies.return_value = {
            'messages': [
                {'ts': '1234567890.000001', 'user': 'U12345'},  # Original message
                {'ts': '1234567890.000002', 'user': 'test-bot-id'}  # Bot reply
            ]
        }
        
        result = self.handler.has_bot_responded('C12345', '1234567890.000001')
        
        # Should detect bot response
        self.assertTrue(result)
        
        # Verify API call
        self.mock_app.client.conversations_replies.assert_called_once_with(
            channel='C12345',
            ts='1234567890.000001',
            limit=10
        )
    
    def test_has_bot_responded_false(self):
        """Test detection of no bot response."""
        # Set up mock response with no bot reply
        self.mock_app.client.conversations_replies.return_value = {
            'messages': [
                {'ts': '1234567890.000001', 'user': 'U12345'},  # Original message
                {'ts': '1234567890.000002', 'user': 'U54321'}  # Another user's reply
            ]
        }
        
        result = self.handler.has_bot_responded('C12345', '1234567890.000001')
        
        # Should not detect bot response
        self.assertFalse(result)
    
    def test_add_reaction(self):
        """Test adding reaction."""
        self.handler.add_reaction('C12345', '1234567890.000001', 'eyes')
        
        # Verify API call
        self.mock_app.client.reactions_add.assert_called_once_with(
            channel='C12345',
            timestamp='1234567890.000001',
            name='eyes'
        )
    
    def test_remove_reaction(self):
        """Test removing reaction."""
        self.handler.remove_reaction('C12345', '1234567890.000001', 'eyes')
        
        # Verify API call
        self.mock_app.client.reactions_remove.assert_called_once_with(
            channel='C12345',
            timestamp='1234567890.000001',
            name='eyes'
        )
    
    def test_update_reaction(self):
        """Test updating reaction."""
        self.handler.update_reaction('C12345', '1234567890.000001', 'eyes', 'white_check_mark')
        
        # Verify API calls
        self.mock_app.client.reactions_remove.assert_called_once_with(
            channel='C12345',
            timestamp='1234567890.000001',
            name='eyes'
        )
        self.mock_app.client.reactions_add.assert_called_once_with(
            channel='C12345',
            timestamp='1234567890.000001',
            name='white_check_mark'
        )
    
    def test_handle_message_duplicate_event(self):
        """Test handling duplicate event."""
        # Set up mock for duplicate event
        self.mock_storage.is_duplicate_event.return_value = True
        
        event = {
            'channel': 'C12345',
            'user': 'U12345',
            'ts': '1234567890.123456',
            'text': 'test message'
        }
        mock_say = MagicMock()
        mock_ack = MagicMock()
        
        self.handler.handle_message(event, mock_say, mock_ack)
        
        # Verify duplicate check
        self.mock_storage.is_duplicate_event.assert_called_once()
        
        # Verify no further processing
        mock_say.assert_not_called()
        self.mock_knowledge_base.query.assert_not_called()
    
    def test_handle_message_already_responded(self):
        """Test handling message already responded to."""
        # Set up mocks
        self.mock_storage.is_duplicate_event.return_value = False
        
        # Mock has_bot_responded to return True
        with patch.object(self.handler, 'has_bot_responded', return_value=True):
            event = {
                'channel': 'C12345',
                'user': 'U12345',
                'ts': '1234567890.123456',
                'text': 'test message'
            }
            mock_say = MagicMock()
            mock_ack = MagicMock()
            
            self.handler.handle_message(event, mock_say, mock_ack)
            
            # Verify response check
            self.handler.has_bot_responded.assert_called_once_with('C12345', '1234567890.123456')
            
            # Verify no further processing
            mock_say.assert_not_called()
            self.mock_knowledge_base.query.assert_not_called()
    
    def test_handle_message_success(self):
        """Test successful message handling."""
        # Set up mocks
        self.mock_storage.is_duplicate_event.return_value = False
        self.mock_storage.get_session_context.return_value = ('test-session', None)
        self.mock_knowledge_base.query.return_value = ('test response', 'new-session')
        
        # Mock has_bot_responded to return False
        with patch.object(self.handler, 'has_bot_responded', return_value=False):
            # Mock add_reaction and update_reaction
            with patch.object(self.handler, 'add_reaction') as mock_add_reaction:
                with patch.object(self.handler, 'update_reaction') as mock_update_reaction:
                    event = {
                        'channel': 'C12345',
                        'user': 'U12345',
                        'ts': '1234567890.123456',
                        'text': 'test message',
                        'thread_ts': '1234567890.000001'
                    }
                    mock_say = MagicMock()
                    mock_ack = MagicMock()
                    
                    self.handler.handle_message(event, mock_say, mock_ack, is_dm=True)
                    
                    # Verify acknowledgement
                    mock_ack.assert_called_once()
                    
                    # Verify reaction added
                    mock_add_reaction.assert_called_once_with('C12345', '1234567890.123456', 'eyes')
                    
                    # Verify context retrieved
                    self.mock_storage.get_session_context.assert_called_once_with('1234567890.000001', 'C12345')
                    
                    # Verify knowledge base queried
                    self.mock_knowledge_base.query.assert_called_once_with('test message', 'test-session', None)
                    
                    # Verify context stored
                    self.mock_storage.store_session_context.assert_called_once_with(
                        '1234567890.000001', 'C12345', 'new-session', 'test message', 'test response'
                    )
                    
                    # Verify response sent
                    mock_say.assert_called_once_with(
                        text='test response',
                        thread_ts='1234567890.000001'
                    )
                    
                    # Verify reaction updated
                    mock_update_reaction.assert_called_once_with(
                        'C12345', '1234567890.123456', 'eyes', 'white_check_mark'
                    )
    
    def test_handle_message_error(self):
        """Test error handling in message processing."""
        # Set up mocks
        self.mock_storage.is_duplicate_event.return_value = False
        self.mock_storage.get_session_context.return_value = (None, None)
        self.mock_knowledge_base.query.side_effect = Exception("Test error")
        
        # Mock has_bot_responded to return False
        with patch.object(self.handler, 'has_bot_responded', return_value=False):
            # Mock add_reaction and update_reaction
            with patch.object(self.handler, 'add_reaction') as mock_add_reaction:
                with patch.object(self.handler, 'update_reaction') as mock_update_reaction:
                    event = {
                        'channel': 'C12345',
                        'user': 'U12345',
                        'ts': '1234567890.123456',
                        'text': '<@test-bot-id> test message',
                        'thread_ts': '1234567890.000001'
                    }
                    mock_say = MagicMock()
                    mock_ack = MagicMock()
                    
                    self.handler.handle_message(event, mock_say, mock_ack, is_dm=False)
                    
                    # Verify reaction updated to error
                    mock_update_reaction.assert_called_once_with(
                        'C12345', '1234567890.123456', 'eyes', 'x'
                    )
                    
                    # Verify error response sent
                    mock_say.assert_called_once()
                    args, kwargs = mock_say.call_args
                    self.assertIn('error', kwargs['text'].lower())
                    self.assertEqual(kwargs['thread_ts'], '1234567890.000001')
    
    def test_register_handlers_with_dm_enabled(self):
        """Test registering event handlers with DM enabled."""
        # Mock config with DM enabled
        with patch('oscar.slack_handler.config') as mock_config:
            mock_config.enable_dm = True
            
            self.handler.register_handlers()
            
            # Verify both event handlers registered
            self.mock_app.event.assert_any_call("app_mention")
            self.mock_app.event.assert_any_call("message")
    
    def test_register_handlers_with_dm_disabled(self):
        """Test registering event handlers with DM disabled."""
        # Mock config with DM disabled
        with patch('oscar.slack_handler.config') as mock_config:
            mock_config.enable_dm = False
            
            self.handler.register_handlers()
            
            # Verify only app_mention handler registered
            self.mock_app.event.assert_called_once_with("app_mention")

if __name__ == '__main__':
    unittest.main()