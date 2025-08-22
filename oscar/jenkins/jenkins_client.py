#!/usr/bin/env python3
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
            logger.info(f"🔐 JENKINS CREDENTIALS: Already loaded, skipping")
            return
        
        try:
            logger.info(f"🔐 JENKINS CREDENTIALS: Loading credentials from config")
            # Get the Jenkins API token from config (already loaded from secrets manager)
            jenkins_api_token = config.jenkins_api_token
            
            if not jenkins_api_token:
                logger.error(f"❌ JENKINS CREDENTIALS: JENKINS_API_TOKEN not found in configuration")
                raise ValueError("JENKINS_API_TOKEN not found in configuration")
            
            logger.info(f"🔐 JENKINS CREDENTIALS: Found API token, parsing username:token format")
            # Parse the token in format "username:token"
            if ':' in jenkins_api_token:
                self._username, self._token = jenkins_api_token.split(':', 1)
                self._username = self._username.strip()
                self._token = self._token.strip()
                self._credentials_loaded = True
                logger.info(f"✅ JENKINS CREDENTIALS: Successfully loaded credentials for user: {self._username}")
            else:
                logger.error(f"❌ JENKINS CREDENTIALS: Invalid token format, should be 'username:token'")
                raise ValueError("Jenkins API token format should be 'username:token'")
                
        except Exception as e:
            logger.error(f"❌ JENKINS CREDENTIALS: Error loading credentials: {e}")
            raise Exception(f"Failed to load Jenkins credentials: {str(e)}")
    
    def get_auth(self) -> HTTPBasicAuth:
        """Get HTTP Basic Auth object for requests."""
        logger.info(f"🔐 JENKINS CREDENTIALS: get_auth() called - this triggers credential loading")
        self._load_credentials()
        logger.info(f"🔐 JENKINS CREDENTIALS: Returning HTTPBasicAuth object for user: {self._username}")
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
            
            logger.info(f"🔍 JENKINS CLIENT: Polling queue for build number: {api_url}")
            
            for attempt in range(max_attempts):
                try:
                    response = self.session.get(api_url, auth=auth, timeout=5)
                    
                    if response.status_code == 200:
                        queue_data = response.json()
                        
                        # Check if the job has started executing (has executable field)
                        executable = queue_data.get('executable')
                        if executable and 'number' in executable:
                            build_number = executable['number']
                            logger.info(f"✅ JENKINS CLIENT: Found build number {build_number} after {attempt + 1} attempts")
                            return build_number
                        
                        # If not yet executing, wait a bit before next attempt
                        if attempt < max_attempts - 1:
                            time.sleep(2)
                            logger.info(f"⏳ JENKINS CLIENT: Build not started yet, attempt {attempt + 1}/{max_attempts}")
                    
                    elif response.status_code == 404:
                        # Queue item might have been processed and removed
                        logger.info(f"⚠️ JENKINS CLIENT: Queue item not found (404), job may have started")
                        break
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"⚠️ JENKINS CLIENT: Error polling queue (attempt {attempt + 1}): {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(2)
            
            logger.info(f"⏰ JENKINS CLIENT: Could not get build number after {max_attempts} attempts")
            return None
            
        except Exception as e:
            logger.error(f"❌ JENKINS CLIENT: Error getting build number from queue: {e}")
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
            logger.info(f"🚀 JENKINS CLIENT: trigger_job called for job_name='{job_name}' with parameters={parameters}")
            logger.info(f"🚀 JENKINS CLIENT: This method WILL make HTTP requests to Jenkins")
            
            # Validate job exists and parameters
            job_def = job_registry.get_job(job_name)
            if not job_def:
                logger.error(f"❌ JENKINS CLIENT: Unknown job '{job_name}'")
                return {
                    'status': 'error',
                    'message': f'Unknown job: {job_name}',
                    'available_jobs': job_registry.list_jobs()
                }
            
            logger.info(f"✅ JENKINS CLIENT: Job '{job_name}' found, validating parameters")
            
            # Validate and normalize parameters
            try:
                validated_params = job_registry.validate_job_parameters(job_name, parameters)
                logger.info(f"✅ JENKINS CLIENT: Parameters validated: {validated_params}")
            except ValueError as e:
                logger.error(f"❌ JENKINS CLIENT: Parameter validation failed: {e}")
                return {
                    'status': 'error',
                    'message': f'Parameter validation failed: {str(e)}',
                    'job_info': job_registry.get_job_info(job_name)
                }
            
            # Build the request
            url = config.get_build_with_parameters_url(job_name)
            logger.info(f"🌐 JENKINS CLIENT: About to load credentials for HTTP request")
            auth = self.credentials.get_auth()
            
            logger.info(f"🌐 JENKINS CLIENT: Making HTTP POST request to Jenkins")
            logger.info(f"🌐 JENKINS CLIENT: URL: {url}")
            logger.info(f"🌐 JENKINS CLIENT: Parameters: {validated_params}")
            logger.info(f"🌐 JENKINS CLIENT: Equivalent curl: curl -XPOST {url} " + 
                       " ".join([f"--data {k}={v}" for k, v in validated_params.items()]) + 
                       f" --user {self.credentials.get_curl_auth_string()}")
            
            # Make the request
            logger.info(f"🌐 JENKINS CLIENT: Executing HTTP POST request NOW")
            response = self.session.post(
                url,
                data=validated_params,
                auth=auth,
                allow_redirects=False  # Jenkins returns 201 with Location header
            )
            
            logger.info(f"🌐 JENKINS CLIENT: HTTP request completed with status: {response.status_code}")
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
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
                        logger.info(f"✅ JENKINS CLIENT: Got build number {build_number}, workflow URL: {result['workflow_url']}")
                
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
            logger.info(f"📋 JENKINS CLIENT: get_job_info called for job_name='{job_name}'")
            logger.info(f"📋 JENKINS CLIENT: This method should NOT make HTTP requests")
            
            # Check if we know about this job
            job_def = job_registry.get_job(job_name)
            if not job_def:
                logger.warning(f"⚠️ JENKINS CLIENT: Unknown job '{job_name}'")
                return {
                    'status': 'error',
                    'message': f'Unknown job: {job_name}',
                    'available_jobs': job_registry.list_jobs()
                }
            
            logger.info(f"✅ JENKINS CLIENT: Found job definition for '{job_name}'")
            logger.info(f"📋 JENKINS CLIENT: Job description: {job_def.description}")
            logger.info(f"📋 JENKINS CLIENT: Job parameters: {list(job_def.get_parameter_info().keys())}")
            
            # Return job definition info (don't need to call Jenkins API for this)
            result = {
                'status': 'success',
                'job_name': job_name,
                'description': job_def.description,
                'job_url': config.get_job_url(job_name),
                'parameter_definitions': job_def.get_parameter_info(),
                'jenkins_url': config.jenkins_url
            }
            
            logger.info(f"✅ JENKINS CLIENT: get_job_info completed successfully for '{job_name}' - NO HTTP REQUESTS MADE")
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