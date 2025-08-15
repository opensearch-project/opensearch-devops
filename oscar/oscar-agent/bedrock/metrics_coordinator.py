#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Metrics Coordinator Module for OSCAR Agent.

This module handles Lambda function invocation for metrics coordination
and processing within the OSCAR agent system.
"""

import json
import logging
from typing import Any, Dict

import boto3

logger = logging.getLogger(__name__)


class MetricsCoordinator:
    """Coordinates metrics analysis through Lambda function invocations."""
    
    def __init__(self, region: str):
        """
        Initialize the metrics coordinator.
        
        Args:
            region: AWS region for Lambda service
        """
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        
        # Metrics Lambda function ARNs (from environment or defaults)
        self.metrics_functions = {
            'test': 'oscar-test-metrics-agent',
            'build': 'oscar-build-metrics-agent', 
            'release': 'oscar-release-metrics-agent',
            'deployment': 'oscar-deployment-metrics-agent'
        }
        
        logger.info(f"Initialized MetricsCoordinator for region: {self.region}")
    
    def invoke_metrics_function(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a metrics Lambda function.
        
        Args:
            function_name: Name of the Lambda function to invoke
            payload: Payload to send to the function
            
        Returns:
            The response from the Lambda function
            
        Raises:
            Exception: If the function invocation fails
        """
        try:
            logger.info(f"Invoking metrics function: {function_name}")
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse the response
            response_payload = json.loads(response['Payload'].read())
            
            # Check for function errors
            if response.get('FunctionError'):
                logger.error(f"Metrics function error: {response_payload}")
                raise Exception(f"Metrics function error: {response_payload}")
            
            logger.info(f"Successfully invoked metrics function: {function_name}")
            return response_payload
            
        except Exception as e:
            logger.error(f"Error invoking metrics function {function_name}: {e}")
            raise
    
    def get_available_functions(self) -> Dict[str, str]:
        """
        Get the available metrics functions.
        
        Returns:
            Dictionary mapping function types to function names
        """
        return self.metrics_functions.copy()