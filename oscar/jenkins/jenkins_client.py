#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Jenkins Client Implementation

This module provides the core Jenkins client functionality for triggering jobs,
checking status, and managing Jenkins operations through the REST API.
"""

import json
import logging
import requests
import time
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urljoin

from config import config
from job_definitions import job_registry

logger = logging.getLogger(__name__)

class JenkinsCredentials:
    """Manages Jenkins credentials from configuration."""
    
    def __init__(self):
        self._username: Optional[str] = None
        self._token: Optional[str] = None
        self._credentials_loaded = False
    
    def _load_credentials(self) -> None:
        """Load credentials from configuration (already loaded from secrets manager)."""
        if self._credentials_loaded:
            logger.info(f"JENKINS CREDENTIALS: Already loaded, skipping")
            return
        
        try:
            jenkins_api_token = config.jenkins_api_token
            
            if not jenkins_api_token:
                raise ValueError("JENKINS_API_TOKEN not found in configuration")
            
            if ':' in jenkins_api_token:
                self._username, self._token = jenkins_api_token.split(':', 1)
                self._username = self._username.strip()
                self._token = self._token.strip()
                self._credentials_loaded = True
            else:
                raise ValueError("Jenkins API token format should be 'username:token'")
                
        except Exception as e:
            raise Exception(f"Failed to load Jenkins credentials: {str(e)}")
    
    def get_auth(self) -> HTTPBasicAuth:
        """Get HTTP Basic Auth object for requests."""
        self._load_credentials()
        return HTTPBasicAuth(self._username, self._token)
    
    def get_username(self) -> str:
        """Get the Jenkins username."""
        self._load_credentials()
        return self._username
    
    def get_curl_auth_string(self) -> str:
        """Get the auth string for curl commands (for logging/debugging)."""
        self._load_credentials()
        return f"{self._username}:***"

class JenkinsClient:
    """Main Jenkins client for job operations."""
    
    def __init__(self):
        self.credentials = JenkinsCredentials()
        self.session = requests.Session()
        self.session.timeout = config.request_timeout
    
    def _get_build_number_from_queue(self, queue_location: str, auth: HTTPBasicAuth, max_attempts: int = 15) -> Optional[int]:
        """
        Poll the Jenkins queue to get the build number once the job starts executing.
        
        Args:
            queue_location: The queue location URL returned by Jenkins
            auth: Authentication object
            max_attempts: Maximum number of polling attempts
            
        Returns:
            Build number if found, None otherwise
        """
        try:
            # Convert queue location to API URL
            if not queue_location.endswith('/api/json'):
                api_url = queue_location.rstrip('/') + '/api/json'
            else:
                api_url = queue_location
            
            logger.info(f"JENKINS CLIENT: Polling queue for build number: {api_url}")
            
            for attempt in range(max_attempts):
                try:
                    response = self.session.get(api_url, auth=auth, timeout=5)
                    
                    if response.status_code == 200:
                        queue_data = response.json()
                        
                        # Check if the job has started executing (has executable field)
                        executable = queue_data.get('executable')
                        if executable and 'number' in executable:
                            build_number = executable['number']
    
                            return build_number
                        
                        # If not yet executing, wait a bit before next attempt
                        if attempt < max_attempts - 1:
                            time.sleep(2)

                    
                    elif response.status_code == 404:
                        # Queue item might have been processed and removed

                        break
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"JENKINS CLIENT: Error polling queue (attempt {attempt + 1}): {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(2)
            

            return None
            
        except Exception as e:
            logger.error(f"JENKINS CLIENT: Error getting build number from queue: {e}")
            return None
    
    def trigger_job(self, job_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a Jenkins job with parameters.
        
        Args:
            job_name: Name of the Jenkins job
            parameters: Dictionary of job parameters
            
        Returns:
            Dictionary containing the result of the job trigger
        """
        try:
            
            # Validate job exists and parameters
            job_def = job_registry.get_job(job_name)
            if not job_def:
                logger.error(f"JENKINS CLIENT: Unknown job '{job_name}'")
                return {
                    'status': 'error',
                    'message': f'Unknown job: {job_name}',
                    'available_jobs': job_registry.list_jobs()
                }
            

            
            # Validate and normalize parameters
            try:
                validated_params = job_registry.validate_job_parameters(job_name, parameters)

            except ValueError as e:
                logger.error(f"JENKINS CLIENT: Parameter validation failed: {e}")
                return {
                    'status': 'error',
                    'message': f'Parameter validation failed: {str(e)}',
                    'job_info': job_registry.get_job_info(job_name)
                }
            
            # Build the request
            url = config.get_build_with_parameters_url(job_name)
            auth = self.credentials.get_auth()
            response = self.session.post(
                url,
                data=validated_params,
                auth=auth,
                allow_redirects=False  # Jenkins returns 201 with Location header
            )
            

            
            if response.status_code in [200, 201]:
                # Success - job triggered
                queue_location = response.headers.get('Location', '')
                
                result = {
                    'status': 'success',
                    'message': f'Successfully triggered Jenkins job: {job_name}',
                    'job_name': job_name,
                    'job_url': config.get_job_url(job_name),
                    'parameters': validated_params,
                    'http_status': response.status_code
                }
                
                if queue_location:
                    result['queue_location'] = queue_location
                    
                    # Try to get the build number from the queue
                    build_number = self._get_build_number_from_queue(queue_location, auth)
                    if build_number:
                        result['build_number'] = build_number
                        result['workflow_url'] = config.get_workflow_url(job_name, build_number)

                
                return result
            
            else:
                # Error response
                error_message = response.text[:500] if response.text else 'Unknown error'
                return {
                    'status': 'error',
                    'message': f'Failed to trigger Jenkins job: {job_name}',
                    'error': f'HTTP {response.status_code}: {error_message}',
                    'http_status': response.status_code,
                    'job_url': config.get_job_url(job_name)
                }
                
        except requests.exceptions.Timeout:
            return {
                'status': 'error',
                'message': f'Request timed out after {config.request_timeout} seconds',
                'error': 'timeout',
                'job_name': job_name
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'status': 'error',
                'message': 'Failed to connect to Jenkins server',
                'error': f'Connection error: {str(e)}',
                'jenkins_url': config.jenkins_url
            }
        except Exception as e:
            logger.error(f"Unexpected error triggering job {job_name}: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Unexpected error triggering job: {job_name}',
                'error': str(e)
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Jenkins server.
        
        Returns:
            Dictionary containing connection test results
        """
        try:
            url = f"{config.jenkins_url}/api/json"
            auth = self.credentials.get_auth()
            
            logger.info("Testing Jenkins connection")
            logger.info(f"URL: {url}")
            
            response = self.session.get(url, auth=auth)
            
            if response.status_code == 200:
                try:
                    jenkins_info = response.json()
                    return {
                        'status': 'success',
                        'message': 'Successfully connected to Jenkins',
                        'jenkins_version': jenkins_info.get('version', 'unknown'),
                        'node_name': jenkins_info.get('nodeName', 'unknown'),
                        'num_executors': jenkins_info.get('numExecutors', 0),
                        'jenkins_url': config.jenkins_url,
                        'username': self.credentials.get_username()
                    }
                except json.JSONDecodeError:
                    return {
                        'status': 'success',
                        'message': 'Successfully connected to Jenkins',
                        'jenkins_url': config.jenkins_url,
                        'username': self.credentials.get_username(),
                        'note': 'Connected but could not parse server info'
                    }
            else:
                return {
                    'status': 'error',
                    'message': f'Jenkins connection failed with HTTP status: {response.status_code}',
                    'error': response.text[:200] if response.text else 'No error details',
                    'http_status': response.status_code,
                    'jenkins_url': config.jenkins_url
                }
                
        except requests.exceptions.Timeout:
            return {
                'status': 'error',
                'message': f'Connection test timed out after {config.request_timeout} seconds',
                'error': 'timeout',
                'jenkins_url': config.jenkins_url
            }
        except requests.exceptions.ConnectionError as e:
            return {
                'status': 'error',
                'message': 'Failed to connect to Jenkins server',
                'error': f'Connection error: {str(e)}',
                'jenkins_url': config.jenkins_url
            }
        except Exception as e:
            logger.error(f"Unexpected error testing connection: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': 'Unexpected error testing Jenkins connection',
                'error': str(e),
                'jenkins_url': config.jenkins_url
            }
    
    def get_job_info(self, job_name: str) -> Dict[str, Any]:
        """
        Get information about a Jenkins job.
        
        Args:
            job_name: Name of the Jenkins job
            
        Returns:
            Dictionary containing job information
        """
        try:
            
            # Check if we know about this job
            job_def = job_registry.get_job(job_name)
            if not job_def:
                logger.warning(f"JENKINS CLIENT: Unknown job '{job_name}'")
                return {
                    'status': 'error',
                    'message': f'Unknown job: {job_name}',
                    'available_jobs': job_registry.list_jobs()
                }
            

            
            # Return job definition info (don't need to call Jenkins API for this)
            result = {
                'status': 'success',
                'job_name': job_name,
                'description': job_def.description,
                'job_url': config.get_job_url(job_name),
                'parameter_definitions': job_def.get_parameter_info(),
                'jenkins_url': config.jenkins_url
            }
            

            return result
                
        except Exception as e:
            logger.error(f"Error getting job info for {job_name}: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Error getting job info: {job_name}',
                'error': str(e)
            }
    
    def list_available_jobs(self) -> Dict[str, Any]:
        """
        List all available Jenkins jobs that this client supports.
        
        Returns:
            Dictionary containing available jobs and their information
        """
        jobs_info = {}
        for job_name in job_registry.list_jobs():
            jobs_info[job_name] = job_registry.get_job_info(job_name)
        
        return {
            'status': 'success',
            'message': 'Available Jenkins jobs',
            'jobs': jobs_info,
            'total_jobs': len(jobs_info)
        }