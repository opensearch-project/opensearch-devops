#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Tests for the bedrock module.
"""

import unittest
from unittest.mock import patch, MagicMock
from abc import ABC, abstractmethod
import os
import sys

# Add the parent directory to sys.path to import the modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Set required environment variables for testing
os.environ['KNOWLEDGE_BASE_ID'] = 'test-kb-id'
os.environ['SLACK_BOT_TOKEN'] = 'test-slack-token'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret'

# Import the modules directly - we'll mock config in individual tests if needed
from bedrock import KnowledgeBaseInterface, BedrockKnowledgeBase, get_knowledge_base

# Define MockKnowledgeBase in the test file
class MockKnowledgeBase(KnowledgeBaseInterface):
    """Mock implementation of knowledge base interface for testing."""
    
    def __init__(self):
        """Initialize mock knowledge base."""
        self.session_counter = 0
    
    def query(self, query, session_id=None, context_summary=None):
        """Mock query implementation."""
        # Generate a mock session ID if none provided
        if not session_id:
            self.session_counter += 1
            session_id = f"mock-session-{self.session_counter}"
        
        # Generate a mock response
        if context_summary:
            response = f"Mock response to '{query}' with context: {context_summary[:50]}..."
        else:
            response = f"Mock response to '{query}'"
        
        return response, session_id

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

if __name__ == '__main__':
    unittest.main()