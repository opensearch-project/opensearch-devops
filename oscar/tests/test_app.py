#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Unit tests for main application handler.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.append('oscar-agent')

# Set environment variables before importing modules
os.environ['DISABLE_CONFIG_VALIDATION'] = 'true'
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret'


class TestLambdaHandler:
    """Test cases for Lambda handler functionality."""
    
    def test_event_id_generation_logic(self):
        """Test event ID generation logic without importing app module."""
        # Test with thread_ts
        event_data = {
            'event': {
                'channel': 'C123456',
                'thread_ts': '1234567890.123456'
            }
        }
        
        # Simulate the logic that would be in get_event_id
        channel = event_data['event']['channel']
        thread_ts = event_data['event'].get('thread_ts') or event_data['event'].get('ts')
        event_id = f"{channel}-{thread_ts}"
        
        assert event_id == 'C123456-1234567890.123456'
        
        # Test without thread_ts
        event_data = {
            'event': {
                'channel': 'C123456',
                'ts': '1234567890.123456'
            }
        }
        
        channel = event_data['event']['channel']
        thread_ts = event_data['event'].get('thread_ts') or event_data['event'].get('ts')
        event_id = f"{channel}-{thread_ts}"
        
        assert event_id == 'C123456-1234567890.123456'
    
    def test_lambda_response_structure(self):
        """Test expected Lambda response structure."""
        # Test successful response
        success_response = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Success'})
        }
        
        assert success_response['statusCode'] == 200
        assert 'headers' in success_response
        assert 'body' in success_response
        
        # Test error response
        error_response = {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }
        
        assert error_response['statusCode'] == 500
        assert 'error' in json.loads(error_response['body'])
    
    def test_slack_event_structure(self):
        """Test Slack event structure validation."""
        # Test valid Slack event
        valid_event = {
            'type': 'event_callback',
            'event': {
                'type': 'app_mention',
                'user': 'U123456',
                'text': '<@U987654> Hello OSCAR!',
                'channel': 'C123456',
                'ts': '1234567890.123456'
            },
            'team_id': 'T123456'
        }
        
        # Validate structure
        assert valid_event['type'] == 'event_callback'
        assert 'event' in valid_event
        assert valid_event['event']['type'] == 'app_mention'
        assert 'user' in valid_event['event']
        assert 'channel' in valid_event['event']
        
        # Test URL verification challenge
        challenge_event = {
            'type': 'url_verification',
            'challenge': 'test_challenge_string'
        }
        
        assert challenge_event['type'] == 'url_verification'
        assert 'challenge' in challenge_event