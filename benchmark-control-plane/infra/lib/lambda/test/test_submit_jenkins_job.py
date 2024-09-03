import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import json
from botocore.exceptions import ClientError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import submit_jenkins_job


@pytest.fixture
def mock_get_secret(mocker):
    return mocker.patch('submit_jenkins_job.get_secret', return_value='fake_token')


@pytest.fixture
def mock_requests_post(mocker):
    return mocker.patch('submit_jenkins_job.requests.post')


@pytest.fixture
def mock_jenkins(mocker):
    return mocker.patch('submit_jenkins_job.jenkins.Jenkins')


def test_successful_benchmark_run(mock_get_secret, mock_requests_post, mock_jenkins):
    # Mock the necessary function calls
    mock_requests_post.return_value.json.return_value = {
        'jobs': {
            'benchmark-pull-request': {'id': '12345'}
        }
    }
    mock_jenkins.return_value.get_queue_item.return_value = {
        'why': None,
        'executable': {'url': 'https://dummy-jenkins-url.com/job/12345'}
    }

    # Prepare the test event
    event = {
        'resource': 'submitBenchmarkRun',
        'body': json.dumps({
            'pull_request_number': '123',
            'repository': 'test-repo'
        })
    }

    # Call the handler function
    result = submit_jenkins_job.handler(event, None)

    # Assert the result
    assert result['statusCode'] == 200
    assert json.loads(result['body']) == {"job_url": "https://dummy-jenkins-url.com/job/12345"}


def test_jenkins_request_exception(mock_get_secret, mock_requests_post):
    # Mock the necessary function calls
    mock_requests_post.side_effect = Exception("Connection error")

    # Prepare the test event
    event = {
        'resource': 'submitBenchmarkRun',
        'body': json.dumps({})
    }

    # Call the handler function
    result = submit_jenkins_job.handler(event, None)

    # Assert the result
    assert result['statusCode'] == 500
    assert "Error: Connection error" in result['body']
    mock_get_secret.assert_called_once_with('benchmark-job-token')


def test_benchmark_endpoint_run(mock_get_secret, mock_requests_post, mock_jenkins):
    # Mock the necessary function calls
    mock_requests_post.return_value.json.return_value = {
        'jobs': {
            'benchmark-test-endpoint': {'id': '67890'}
        }
    }
    mock_jenkins.return_value.get_queue_item.return_value = {
        'why': None,
        'executable': {'url': 'https://dummy-jenkins-url.com/job/67890'}
    }

    # Prepare the test event
    event = {
        'resource': 'submitBenchmarkEndpointRun',
        'body': json.dumps({
            'endpoint': 'test-endpoint'
        })
    }

    # Call the handler function
    result = submit_jenkins_job.handler(event, None)

    # Assert the result
    assert result['statusCode'] == 200
    assert json.loads(result['body']) == {"job_url": "https://dummy-jenkins-url.com/job/67890"}
    mock_get_secret.assert_called_once_with('benchmark-endpoint-job-token')
