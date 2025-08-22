#!/usr/bin/env python3
"""
Jenkins Integration Configuration

This module provides centralized configuration for the Jenkins integration,
including job definitions, credentials, and environment settings.
"""

import os
import boto3
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from io import StringIO

logger = logging.getLogger(__name__)

class JenkinsConfig:
    """Centralized configuration for Jenkins integration."""
    
    def __init__(self):
        """Initialize configuration by loading .env from secrets manager and setting up all variables."""
        
        # Load environment variables from AWS Secrets Manager
        self._load_env_from_secrets()
        
        # Jenkins Server Configuration
        self.jenkins_url = os.getenv('JENKINS_URL', 'https://build.ci.opensearch.org')
        self.jenkins_api_token = os.getenv('JENKINS_API_TOKEN')
        self.jenkins_agent_id = os.getenv('JENKINS_AGENT_ID')
        self.jenkins_agent_alias_id = os.getenv('JENKINS_AGENT_ALIAS_ID')
        self.jenkins_lambda_function_name = os.getenv('JENKINS_LAMBDA_FUNCTION_NAME', 'oscar-jenkins-agent')
        
        # AWS Configuration
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.aws_account_id = os.getenv('AWS_ACCOUNT_ID', '395380602281')
        
        # Lambda Configuration
        self.lambda_timeout = int(os.getenv('LAMBDA_TIMEOUT', '180'))
        self.lambda_memory_size = int(os.getenv('LAMBDA_MEMORY_SIZE', '512'))
        
        # Request Configuration
        self.request_timeout = int(os.getenv('JENKINS_REQUEST_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('JENKINS_MAX_RETRIES', '3'))
        
        # Logging Configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # User Access Control - Use existing authorized message senders
        self.authorized_message_senders = self._load_authorized_senders()
        
        # Validate required configuration
        self._validate_config()
    
    def _load_env_from_secrets(self) -> None:
        """Load environment variables from AWS Secrets Manager."""
        try:
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            
            # Get the .env content from secrets manager
            response = client.get_secret_value(SecretId='oscar-central-env')
            env_content = response['SecretString']
            
            # Load the .env content into environment variables
            config_stream = StringIO(env_content)
            load_dotenv(stream=config_stream, override=True)
            
            logger.info("Successfully loaded environment variables from AWS Secrets Manager")
            
        except Exception as e:
            logger.error(f"Error loading environment from secrets manager: {e}")
            logger.warning("Falling back to local environment variables")
            # Continue with local environment variables if secrets manager fails
    
    def _validate_config(self) -> None:
        """Validate that required configuration is present."""
        required_vars = {
            'jenkins_url': self.jenkins_url,
            'aws_region': self.aws_region,
            'aws_account_id': self.aws_account_id
        }
        
        # Jenkins API token is only required in production (Lambda environment)
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            # Lambda environment - validate all including Jenkins token
            required_vars['jenkins_api_token'] = self.jenkins_api_token
            missing_vars = [var for var, value in required_vars.items() if not value]
            
            if missing_vars:
                raise ValueError(f"Missing required configuration variables: {', '.join(missing_vars)}")
            
            logger.info("Full configuration validation passed (Lambda environment)")
        else:
            # Local environment - only validate basic config, warn about missing Jenkins token
            missing_vars = [var for var, value in required_vars.items() if not value]
            if missing_vars:
                logger.warning(f"Missing configuration variables (local environment): {', '.join(missing_vars)}")
            
            if not self.jenkins_api_token:
                logger.warning("Jenkins API token not configured (local environment)")
            
            logger.info("Basic configuration validation passed (local environment)")
        
    def get_job_url(self, job_name: str) -> str:
        """Get the full URL for a Jenkins job."""
        return f"{self.jenkins_url}/job/{job_name}"
    
    def get_build_with_parameters_url(self, job_name: str) -> str:
        """Get the buildWithParameters URL for a Jenkins job."""
        return f"{self.jenkins_url}/job/{job_name}/buildWithParameters"
    
    def get_job_api_url(self, job_name: str) -> str:
        """Get the API URL for a Jenkins job."""
        return f"{self.jenkins_url}/job/{job_name}/api/json"
    
    def get_build_api_url(self, job_name: str, build_number: int) -> str:
        """Get the API URL for a specific build."""
        return f"{self.jenkins_url}/job/{job_name}/{build_number}/api/json"
    
    def get_workflow_url(self, job_name: str, build_number: int) -> str:
        """Get the workflow URL for a specific build."""
        return f"{self.jenkins_url}/job/{job_name}/{build_number}/"
    
    def _load_authorized_senders(self) -> set:
        """Load the list of authorized message senders (same as main OSCAR authorization)."""
        authorized_senders_str = os.getenv('AUTHORIZED_MESSAGE_SENDERS', '')
        if not authorized_senders_str:
            logger.warning("AUTHORIZED_MESSAGE_SENDERS not configured - Jenkins access will be restricted")
            return set()
        
        # Parse comma-separated list of authorized senders
        authorized_senders = {user.strip() for user in authorized_senders_str.split(',') if user.strip()}
        logger.info(f"Loaded {len(authorized_senders)} authorized Jenkins users")
        return authorized_senders
    
    def is_user_authorized(self, user_id: str) -> bool:
        """Check if a user is authorized to use Jenkins functions (same as main OSCAR authorization)."""
        if not user_id:
            return False
        
        # If no authorization list is configured, deny access for security
        if not self.authorized_message_senders:
            logger.warning("No authorized senders configured - denying access")
            return False
        
        return user_id in self.authorized_message_senders

# Global configuration instance
config = JenkinsConfig()