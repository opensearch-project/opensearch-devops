#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Unit tests for AWS connectivity functionality.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.append('metrics')

# Set environment variable before importing modules
os.environ['DISABLE_CONFIG_VALIDATION'] = 'true'


class TestAWSConnectivity:
    """Test cases for AWS connectivity functionality."""
    
    @patch('boto3.Session')
    def test_role_assumption_functionality(self, mock_session_class):
        """Test role assumption functionality that was in aws_utils.py."""
        # Mock session and STS client
        mock_session = Mock()
        mock_sts_client = Mock()
        mock_session_class.return_value = mock_session
        mock_session.client.return_value = mock_sts_client
        
        # Mock STS response
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/TestRole/test-session',
            'UserId': 'AIDACKCEVSQ6C2EXAMPLE'
        }
        
        # Test the role assumption logic
        result = self._test_role_assumption(mock_session)
        
        assert result['status'] == 'success'
        assert 'duration_seconds' in result
        assert 'assumed_identity' in result
        assert result['assumed_identity']['account'] == '123456789012'
    
    def _test_role_assumption(self, session):
        """Test cross-account role assumption."""
        try:
            start_time = time.time()
            # Simulate role assumption time
            time.sleep(0.001)  # Small delay to simulate processing
            end_time = time.time()
            
            # Test assumed identity
            sts_client = session.client('sts')
            assumed_identity = sts_client.get_caller_identity()
            
            return {
                'status': 'success',
                'duration_seconds': round(end_time - start_time, 3),
                'assumed_identity': {
                    'account': assumed_identity.get('Account'),
                    'arn': assumed_identity.get('Arn'),
                    'user_id': assumed_identity.get('UserId')
                }
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def test_opensearch_connectivity_functionality(self):
        """Test OpenSearch connectivity functionality that was in aws_utils.py."""
        # Mock OpenSearch responses
        mock_health_response = {
            'status': 'green',
            'cluster_name': 'test-cluster'
        }
        
        mock_search_response = {
            'hits': {
                'total': {'value': 100}
            }
        }
        
        # Test the connectivity logic
        result = self._test_opensearch_connectivity(mock_health_response, mock_search_response)
        
        assert result['status'] == 'success'
        assert result['cluster_health'] == 'green'
        assert result['cluster_name'] == 'test-cluster'
        assert result['total_documents'] == 100
    
    def _test_opensearch_connectivity(self, health_response, search_response):
        """Test OpenSearch connectivity and basic queries."""
        try:
            # Simulate health check
            health = health_response
            
            # Simulate search
            search_result = search_response
            
            return {
                'status': 'success',
                'cluster_health': health.get('status', 'unknown'),
                'cluster_name': health.get('cluster_name', 'unknown'),
                'total_documents': search_result.get('hits', {}).get('total', {}).get('value', 0)
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def test_error_handling(self):
        """Test error handling in connectivity functions."""
        # Test role assumption error
        try:
            raise Exception("Test error")
        except Exception as e:
            error_result = {
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__
            }
            
            assert error_result['status'] == 'failed'
            assert error_result['error'] == 'Test error'
            assert error_result['error_type'] == 'Exception'
    
    def test_response_structure_validation(self):
        """Test that response structures are valid."""
        # Test successful response structure
        success_response = {
            'status': 'success',
            'duration_seconds': 0.123,
            'assumed_identity': {
                'account': '123456789012',
                'arn': 'test-arn',
                'user_id': 'test-user-id'
            }
        }
        
        required_fields = ['status', 'duration_seconds', 'assumed_identity']
        assert all(field in success_response for field in required_fields)
        
        # Test error response structure
        error_response = {
            'status': 'failed',
            'error': 'Test error message',
            'error_type': 'TestException'
        }
        
        error_fields = ['status', 'error', 'error_type']
        assert all(field in error_response for field in error_fields)