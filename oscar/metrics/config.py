#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Configuration Management for Metrics Lambda Functions.

This module provides centralized configuration management for the metrics
Lambda functions, handling environment variables, validation, and default values.

Classes:
    MetricsConfig: Main configuration class with validation and environment variable handling
"""

from typing import Optional
import os
import boto3
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from io import StringIO

logger = logging.getLogger(__name__)




class MetricsConfig:
    """Centralized configuration management for Metrics Lambda Functions.
    
    This class handles all configuration aspects including environment variables,
    validation, and default values for the metrics processing system.
    """
    
    def __init__(self, validate_required: bool = True) -> None:
        """Initialize configuration with environment variables.
        
        Args:
            validate_required: Whether to validate required environment variables
            
        Raises:
            ValueError: If required environment variables are missing
        """
        self._load_env_from_secrets()
        # AWS region
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # OpenSearch configuration
        self.opensearch_host = os.environ.get('OPENSEARCH_HOST', '')
        self.opensearch_vpc_endpoint_url = os.environ.get('OPENSEARCH_VPC_ENDPOINT_URL', '')
        self.opensearch_domain_arn = os.environ.get('OPENSEARCH_DOMAIN_ARN', '')
        self.opensearch_domain_account = os.environ.get('OPENSEARCH_DOMAIN_ACCOUNT', '979020455945')
        self.opensearch_region = os.environ.get('OPENSEARCH_REGION', 'us-east-1')
        self.opensearch_service = os.environ.get('OPENSEARCH_SERVICE', 'es')
        
        # Cross-account role configuration
        self.metrics_cross_account_role_arn = os.environ.get(
            'METRICS_CROSS_ACCOUNT_ROLE_ARN', 
            'arn:aws:iam::979020455945:role/OpenSearchOscarAccessRole'
        )
        
        # Query configuration
        self.request_timeout = int(os.environ.get('REQUEST_TIMEOUT', 30))
        self.max_results = int(os.environ.get('MAX_RESULTS', 1000))
        self.default_query_size = int(os.environ.get('OPENSEARCH_DEFAULT_QUERY_SIZE', 500))
        self.large_query_size = int(os.environ.get('OPENSEARCH_LARGE_QUERY_SIZE', 1000))
        self.opensearch_request_timeout = int(os.environ.get('OPENSEARCH_REQUEST_TIMEOUT', 60))
        
        # Index names
        self.integration_test_index = os.environ.get(
            'OPENSEARCH_INTEGRATION_TEST_INDEX', 
            'opensearch-integration-test-results-*'
        )
        self.build_results_index = os.environ.get(
            'OPENSEARCH_BUILD_RESULTS_INDEX', 
            'opensearch-distribution-build-results-*'
        )
        self.release_metrics_index = os.environ.get(
            'OPENSEARCH_RELEASE_METRICS_INDEX', 
            'opensearch_release_metrics'
        )
        
        # Logging configuration
        self.log_level = os.environ.get('LOG_LEVEL', 'INFO')
        self.mock_mode = os.environ.get('MOCK_MODE', 'false').lower() == 'true'
        
        # Response configuration
        self.bedrock_message_version = os.environ.get('BEDROCK_RESPONSE_MESSAGE_VERSION', '1.0')
        
        # Validation
        if validate_required:
            if not self.opensearch_host:
                logger.error("OPENSEARCH_HOST environment variable is required")
                raise ValueError("OPENSEARCH_HOST environment variable is required")
        
        logger.info(f"Initialized MetricsConfig - Region: {self.region}, Mock Mode: {self.mock_mode}")

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
    
        
    def get_opensearch_host_clean(self) -> str:
        """Get OpenSearch host with https:// prefix removed.
        
        Returns:
            Clean OpenSearch host without protocol prefix
        """
        return self.opensearch_host.replace('https://', '')
    
    def get_integration_test_index_pattern(self) -> str:
        """Get integration test index pattern for queries.
        
        Returns:
            Index pattern for integration test queries
        """
        return f"{self.integration_test_index}-*"
    
    def get_build_results_index_pattern(self) -> str:
        """Get build results index pattern for queries.
        
        Returns:
            Index pattern for build results queries
        """
        return f"{self.build_results_index}-*"


class _ConfigProxy:
    """Proxy that caches config per lambda execution."""
    def __init__(self):
        self._cached_config = None
        self.aws_request_id = None
        self._lambda_request_id = None
    
    def set_request_id(self, request_id: str) -> None:
        """Set the AWS Lambda request ID."""
        self.aws_request_id = request_id
    
    def __getattr__(self, name):
        # If no config cached yet or request ID changed, create fresh config
        if self._cached_config is None or (self.aws_request_id and self._lambda_request_id != self.aws_request_id):
            self._cached_config = MetricsConfig(validate_required=False)
            self._lambda_request_id = self.aws_request_id
        
        return getattr(self._cached_config, name)

# Global configuration proxy
config = _ConfigProxy()