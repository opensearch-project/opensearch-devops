import json
import sys
import os
from unittest.mock import patch, MagicMock
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from custom_lambda_auth import generate_policy, check_user_permission, lambda_handler


@pytest.fixture
def mock_requests():
    with patch('custom_lambda_auth.requests') as mock:
        yield mock


@pytest.fixture
def mock_boto3():
    with patch('custom_lambda_auth.boto3') as mock:
        yield mock


def test_lambda_handler_valid_token(mock_requests):
    # Mock the GitHub API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'login': 'testuser'}
    mock_requests.get.return_value = mock_response

    # Mock the check_user_permission function
    with patch('custom_lambda_auth.check_user_permission', return_value=True):
        event = {
            'authorizationToken': 'valid_token',
            'methodArn': 'arn:aws:execute-api:us-east-1:123456789012:api-id/stage/method/resource-path'
        }
        result = lambda_handler(event, {})

    assert result['policyDocument']['Statement'][0]['Effect'] == 'Allow'
    assert result['principalId'] == 'testuser'
