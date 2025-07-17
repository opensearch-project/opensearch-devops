"""
Tests for the bedrock module.
"""

import unittest
from unittest.mock import patch, MagicMock
from oscar.bedrock import MockKnowledgeBase, BedrockKnowledgeBase, get_knowledge_base

class TestMockKnowledgeBase(unittest.TestCase):
    """Test cases for the MockKnowledgeBase class."""
    
    def setUp(self):
        """Set up test environment."""
        self.kb = MockKnowledgeBase()
    
    def test_query_without_context(self):
        """Test querying without context or session."""
        response, session_id = self.kb.query("test query")
        
        self.assertIn("test query", response)
        self.assertEqual(session_id, "mock-session-1")
    
    def test_query_with_session(self):
        """Test querying with session ID."""
        response, session_id = self.kb.query("test query", session_id="existing-session")
        
        self.assertIn("test query", response)
        self.assertEqual(session_id, "existing-session")
    
    def test_query_with_context(self):
        """Test querying with context summary."""
        response, session_id = self.kb.query("test query", context_summary="previous context")
        
        self.assertIn("test query", response)
        self.assertIn("context", response)
        self.assertEqual(session_id, "mock-session-1")
    
    def test_session_counter_increments(self):
        """Test that session counter increments for new sessions."""
        _, session_id1 = self.kb.query("query 1")
        _, session_id2 = self.kb.query("query 2")
        
        self.assertEqual(session_id1, "mock-session-1")
        self.assertEqual(session_id2, "mock-session-2")

class TestBedrockKnowledgeBase(unittest.TestCase):
    """Test cases for the BedrockKnowledgeBase class."""
    
    @patch('boto3.client')
    def setUp(self, mock_boto_client):
        """Set up test environment with mocked Bedrock client."""
        # Set up mock Bedrock client
        self.mock_bedrock_client = MagicMock()
        mock_boto_client.return_value = self.mock_bedrock_client
        
        # Set up mock response
        self.mock_bedrock_client.retrieve_and_generate.return_value = {
            'output': {'text': 'test response'},
            'sessionId': 'test-session-id'
        }
        
        # Create knowledge base instance with test config
        with patch('oscar.bedrock.config') as mock_config:
            mock_config.region = 'us-west-2'
            mock_config.knowledge_base_id = 'TEST5FBGMYGHPK'  # Valid format for knowledge base ID
            mock_config.model_arn = 'test-model-arn'
            mock_config.prompt_template = 'test prompt template with $search_results$ and $query$'
            self.kb = BedrockKnowledgeBase()
    
    def test_query_standard_model(self):
        """Test querying with standard foundation model."""
        response, session_id = self.kb.query("test query")
        
        # Verify response
        self.assertEqual(response, "test response")
        self.assertEqual(session_id, "test-session-id")
        
        # Verify API call
        self.mock_bedrock_client.retrieve_and_generate.assert_called_once()
        args, kwargs = self.mock_bedrock_client.retrieve_and_generate.call_args
        
        # Check request structure
        self.assertEqual(kwargs['input']['text'], "test query")
        self.assertEqual(kwargs['retrieveAndGenerateConfiguration']['type'], "KNOWLEDGE_BASE")
        self.assertEqual(kwargs['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['knowledgeBaseId'], "TEST5FBGMYGHPK")
        self.assertEqual(kwargs['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['modelArn'], "test-model-arn")
        self.assertIn('orchestrationConfiguration', kwargs['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration'])
        self.assertIn('generationConfiguration', kwargs['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration'])
    
    @patch('boto3.client')
    def test_query_with_inference_profile(self, mock_boto_client):
        """Test querying with inference profile."""
        # Set up mock client for this test
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.retrieve_and_generate.return_value = {
            'output': {'text': 'test response'},
            'sessionId': 'test-session-id'
        }
        
        # Update model ARN to inference profile
        with patch('oscar.bedrock.config') as mock_config:
            mock_config.region = 'us-west-2'
            mock_config.knowledge_base_id = 'TEST5FBGMYGHPK'  # Valid format for knowledge base ID
            mock_config.model_arn = 'arn:aws:bedrock:us-west-2:123456789012:inference-profile/test-model'
            mock_config.prompt_template = 'test prompt template with $search_results$ and $query$'
            kb = BedrockKnowledgeBase()
        
        response, session_id = kb.query("test query")
        
        # Verify response
        self.assertEqual(response, "test response")
        self.assertEqual(session_id, "test-session-id")
        
        # Verify API call
        mock_client.retrieve_and_generate.assert_called_once()
        args, kwargs = mock_client.retrieve_and_generate.call_args
        
        # Check request structure for inference profile
        self.assertEqual(kwargs['input']['text'], "test query")
        self.assertEqual(kwargs['retrieveAndGenerateConfiguration']['type'], "KNOWLEDGE_BASE")
        self.assertEqual(kwargs['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['knowledgeBaseId'], "TEST5FBGMYGHPK")
        self.assertEqual(kwargs['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['modelArn'], 
                         'arn:aws:bedrock:us-west-2:123456789012:inference-profile/test-model')
        # Should not have orchestrationConfiguration for inference profile
        self.assertNotIn('orchestrationConfiguration', kwargs['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration'])
        self.assertIn('generationConfiguration', kwargs['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration'])
    
    def test_query_with_context(self):
        """Test querying with context summary."""
        response, session_id = self.kb.query("test query", context_summary="previous conversation")
        
        # Verify enhanced query with context
        args, kwargs = self.mock_bedrock_client.retrieve_and_generate.call_args
        self.assertIn("previous conversation", kwargs['input']['text'])
        self.assertIn("test query", kwargs['input']['text'])
    
    def test_query_with_session(self):
        """Test querying with session ID."""
        response, session_id = self.kb.query("test query", session_id="existing-session")
        
        # Verify session ID included in request
        args, kwargs = self.mock_bedrock_client.retrieve_and_generate.call_args
        self.assertEqual(kwargs['sessionId'], "existing-session")
    
    def test_fallback_without_decomposition(self):
        """Test fallback to query without decomposition."""
        # First call fails, second succeeds
        self.mock_bedrock_client.retrieve_and_generate.side_effect = [
            Exception("Query decomposition failed"),
            {'output': {'text': 'fallback response'}, 'sessionId': 'fallback-session'}
        ]
        
        response, session_id = self.kb.query("test query")
        
        # Verify fallback response
        self.assertEqual(response, "fallback response")
        self.assertEqual(session_id, "fallback-session")
        
        # Verify both calls were made
        self.assertEqual(self.mock_bedrock_client.retrieve_and_generate.call_count, 2)

class TestKnowledgeBaseFactory(unittest.TestCase):
    """Test cases for the knowledge base factory function."""
    
    def test_get_mock_knowledge_base(self):
        """Test getting mock knowledge base."""
        kb = get_knowledge_base(kb_type='mock')
        self.assertIsInstance(kb, MockKnowledgeBase)
    
    @patch('oscar.bedrock.BedrockKnowledgeBase')
    def test_get_bedrock_knowledge_base(self, mock_bedrock_kb_class):
        """Test getting Bedrock knowledge base."""
        kb = get_knowledge_base(kb_type='bedrock', region='us-east-1')
        
        # Verify correct class instantiated with region
        mock_bedrock_kb_class.assert_called_once_with('us-east-1')
    
    @patch('oscar.bedrock.BedrockKnowledgeBase')
    def test_default_knowledge_base(self, mock_bedrock_kb_class):
        """Test default knowledge base type."""
        kb = get_knowledge_base()
        
        # Default should be Bedrock
        mock_bedrock_kb_class.assert_called_once()

if __name__ == '__main__':
    unittest.main()