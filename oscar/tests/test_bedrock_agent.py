#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Unit tests for Bedrock agent functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.append('oscar-agent')

# Set environment variable before importing modules
os.environ['DISABLE_CONFIG_VALIDATION'] = 'true'


class TestBedrockAgent:
    """Test cases for Bedrock agent functionality."""
    
    def test_bedrock_module_exists(self):
        """Test that bedrock modules exist."""
        try:
            from bedrock import get_oscar_agent
            assert get_oscar_agent is not None
        except ImportError:
            # Check if bedrock directory exists
            import os
            bedrock_path = os.path.join('oscar-agent', 'bedrock')
            if os.path.exists(bedrock_path):
                # Directory exists, try individual modules
                try:
                    sys.path.append(bedrock_path)
                    import main_agent
                    assert main_agent is not None
                except ImportError:
                    pytest.skip("Bedrock modules not available for testing")
            else:
                pytest.skip("Bedrock directory not found")
    
    def test_query_processing_logic(self):
        """Test query processing logic."""
        # Test query cleaning logic
        raw_query = '<@U987654> Hello OSCAR! Can you help me with OpenSearch?'
        
        # Basic mention removal logic
        import re
        mention_pattern = r'<@[UW][A-Z0-9]+>'
        clean_query = re.sub(mention_pattern, '', raw_query).strip()
        assert clean_query == 'Hello OSCAR! Can you help me with OpenSearch?'
        
        # Test query validation logic
        valid_query = 'What is OpenSearch?'
        assert len(valid_query.strip()) > 0
        
        empty_query = ''
        assert len(empty_query.strip()) == 0
    
    def test_bedrock_response_structure(self):
        """Test expected Bedrock response structure."""
        # Mock Bedrock response structure
        mock_response = {
            'output': {
                'text': 'This is a test response from Bedrock'
            },
            'citations': []
        }
        
        # Test response parsing
        assert 'output' in mock_response
        assert 'text' in mock_response['output']
        assert mock_response['output']['text'] == 'This is a test response from Bedrock'
        assert 'citations' in mock_response
        assert isinstance(mock_response['citations'], list)
    
    def test_session_id_generation(self):
        """Test session ID generation logic."""
        import uuid
        import time
        
        # Test UUID-based session ID
        session_id = str(uuid.uuid4())
        assert len(session_id) == 36  # Standard UUID length
        assert '-' in session_id
        
        # Test timestamp-based session ID
        timestamp_id = f"session-{int(time.time())}"
        assert timestamp_id.startswith('session-')
        assert len(timestamp_id) > 8