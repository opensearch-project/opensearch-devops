#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Jenkins integration components.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add jenkins directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'jenkins'))

from jenkins_client import JenkinsClient, JenkinsCredentials
from job_definitions import DockerScanJob, CentralReleasePromotionJob, job_registry
from lambda_function import lambda_handler, handle_trigger_job, handle_get_job_info


class TestJenkinsCredentials(unittest.TestCase):
    """Test Jenkins credentials management."""
    
    @patch('jenkins_client.config')
    def test_load_credentials_success(self, mock_config):
        """Test successful credential loading."""
        mock_config.jenkins_api_token = 'testuser:testtoken'
        
        creds = JenkinsCredentials()
        auth = creds.get_auth()
        
        self.assertEqual(creds.get_username(), 'testuser')
        self.assertIsNotNone(auth)
    
    @patch('jenkins_client.config')
    def test_load_credentials_invalid_format(self, mock_config):
        """Test credential loading with invalid format."""
        mock_config.jenkins_api_token = 'invalidtoken'
        
        creds = JenkinsCredentials()
        
        with self.assertRaises(Exception):
            creds.get_auth()
    
    @patch('jenkins_client.config')
    def test_load_credentials_missing_token(self, mock_config):
        """Test credential loading with missing token."""
        mock_config.jenkins_api_token = None
        
        creds = JenkinsCredentials()
        
        with self.assertRaises(Exception):
            creds.get_auth()


class TestJobDefinitions(unittest.TestCase):
    """Test job definition classes."""
    
    def test_docker_scan_job(self):
        """Test DockerScanJob definition."""
        job = DockerScanJob()
        
        self.assertEqual(job.job_name, 'docker-scan')
        self.assertIn('IMAGE_FULL_NAME', job.get_parameter_info())
        self.assertTrue(job.get_parameter_info()['IMAGE_FULL_NAME']['required'])
    
    def test_central_release_promotion_job(self):
        """Test CentralReleasePromotionJob definition."""
        job = CentralReleasePromotionJob()
        
        self.assertEqual(job.job_name, 'central-release-promotion')
        params = job.get_parameter_info()
        
        self.assertIn('RELEASE_VERSION', params)
        self.assertIn('OPENSEARCH_RC_BUILD_NUMBER', params)
        self.assertIn('OPENSEARCH_DASHBOARDS_RC_BUILD_NUMBER', params)
        
        # All should be required
        for param in params.values():
            self.assertTrue(param['required'])
    
    def test_job_registry(self):
        """Test job registry functionality."""
        jobs = job_registry.list_jobs()
        
        self.assertIn('docker-scan', jobs)
        self.assertIn('central-release-promotion', jobs)
        
        # Test getting job info
        docker_job = job_registry.get_job('docker-scan')
        self.assertIsNotNone(docker_job)
        
        # Test unknown job
        unknown_job = job_registry.get_job('nonexistent-job')
        self.assertIsNone(unknown_job)
    
    def test_parameter_validation(self):
        """Test job parameter validation."""
        # Valid parameters
        valid_params = {'IMAGE_FULL_NAME': 'alpine:3.19'}
        validated = job_registry.validate_job_parameters('docker-scan', valid_params)
        self.assertEqual(validated, valid_params)
        
        # Missing required parameter
        with self.assertRaises(ValueError):
            job_registry.validate_job_parameters('docker-scan', {})
        
        # Unknown job
        with self.assertRaises(ValueError):
            job_registry.validate_job_parameters('unknown-job', {})


class TestJenkinsClient(unittest.TestCase):
    """Test Jenkins client functionality."""
    
    @patch('jenkins_client.config')
    def setUp(self, mock_config):
        """Set up test client."""
        mock_config.jenkins_api_token = 'testuser:testtoken'
        mock_config.request_timeout = 30
        self.client = JenkinsClient()
    
    def test_get_job_info_success(self):
        """Test successful job info retrieval."""
        result = self.client.get_job_info('docker-scan')
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['job_name'], 'docker-scan')
        self.assertIn('parameter_definitions', result)
    
    def test_get_job_info_unknown_job(self):
        """Test job info for unknown job."""
        result = self.client.get_job_info('unknown-job')
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Unknown job', result['message'])
    
    def test_list_available_jobs(self):
        """Test listing available jobs."""
        result = self.client.list_available_jobs()
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('jobs', result)
        self.assertGreater(result['total_jobs'], 0)


class TestLambdaHandler(unittest.TestCase):
    """Test Lambda handler functionality."""
    
    def test_get_job_info_handler(self):
        """Test get_job_info Lambda handler."""
        event = {
            'function': 'get_job_info',
            'parameters': [
                {'name': 'job_name', 'value': 'docker-scan'}
            ]
        }
        
        result = lambda_handler(event, None)
        
        self.assertIn('response', result)
        self.assertEqual(result['messageVersion'], '1.0')
    
    def test_trigger_job_missing_confirmation(self):
        """Test trigger_job without confirmation."""
        event = {
            'function': 'trigger_job',
            'parameters': [
                {'name': 'job_name', 'value': 'docker-scan'},
                {'name': 'IMAGE_FULL_NAME', 'value': 'alpine:3.19'}
            ]
        }
        
        result = lambda_handler(event, None)
        response_body = result['response']['functionResponse']['responseBody']['TEXT']['body']
        
        self.assertIn('confirmed', response_body)
        self.assertIn('required', response_body)
    
    def test_trigger_job_confirmation_false(self):
        """Test trigger_job with confirmation=false."""
        event = {
            'function': 'trigger_job',
            'parameters': [
                {'name': 'job_name', 'value': 'docker-scan'},
                {'name': 'IMAGE_FULL_NAME', 'value': 'alpine:3.19'},
                {'name': 'confirmed', 'value': 'false'}
            ]
        }
        
        result = lambda_handler(event, None)
        response_body = result['response']['functionResponse']['responseBody']['TEXT']['body']
        
        self.assertIn('cancelled', response_body)
    
    def test_unknown_function(self):
        """Test unknown function handling."""
        event = {
            'function': 'unknown_function',
            'parameters': []
        }
        
        result = lambda_handler(event, None)
        response_body = result['response']['functionResponse']['responseBody']['TEXT']['body']
        
        self.assertIn('Unknown function', response_body)
    
    def test_list_jobs_handler(self):
        """Test list_jobs Lambda handler."""
        event = {
            'function': 'list_jobs',
            'parameters': []
        }
        
        result = lambda_handler(event, None)
        
        self.assertIn('response', result)
        response_body = result['response']['functionResponse']['responseBody']['TEXT']['body']
        self.assertIn('Available Jenkins jobs', response_body)


class TestJobParameterFormatting(unittest.TestCase):
    """Test job parameter formatting utilities."""
    
    def test_format_parameters_as_bullets(self):
        """Test parameter formatting function."""
        from lambda_function import format_parameters_as_bullets
        
        # Test with parameters
        params = {
            'PARAM1': {'description': 'Test param 1', 'required': True},
            'PARAM2': {'description': 'Test param 2', 'required': False, 'default': 'default_value'}
        }
        
        result = format_parameters_as_bullets(params)
        
        self.assertIn('• PARAM1 - Test param 1', result)
        self.assertIn('• PARAM2 (Optional) - Test param 2', result)
        self.assertIn('Default: default_value', result)
    
    def test_format_parameters_empty(self):
        """Test parameter formatting with no parameters."""
        from lambda_function import format_parameters_as_bullets
        
        result = format_parameters_as_bullets({})
        self.assertEqual(result, "• No parameters required")


if __name__ == '__main__':
    unittest.main()