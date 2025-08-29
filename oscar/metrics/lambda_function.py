#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Main Lambda Function for Metrics Processing.

This module provides the main Lambda handler for metrics processing,
coordinating between different modules to provide comprehensive
metrics analysis for the OSCAR system.

Functions:
    lambda_handler: Main Lambda handler for metrics processing
"""

import json
import logging
import uuid
from typing import Any, Dict
import traceback
from helper_functions import handle_component_resolution, handle_rc_build_mapping
from metrics_handler import handle_metrics_query
from response_builder import create_response
from config import config

logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for metrics processing.
    
    Function Mappings:
    
    Integration Test Agent:
    - get_integration_test_metrics: Get integration test results with proper deduplication
    - get_rc_build_mapping: Map RC numbers to build numbers
    
    Build Metrics Agent:
    - get_build_metrics: Get build results and metrics
    - resolve_components_from_builds: Map build numbers to components
    
    Release Metrics Agent:
    - get_release_metrics: Get release readiness metrics
    
    Deprecated Functions (still supported but not recommended):
    - get_test_metrics: Use get_integration_test_metrics instead
    - get_metrics: Too generic, use specific functions instead
    
    Args:
        event: Lambda event containing the action group request
        context: Lambda context
        
    Returns:
        Response for the Bedrock agent
    """
    # Set the Lambda request ID for config caching
    if context and hasattr(context, 'aws_request_id'):
        config.set_request_id(context.aws_request_id)
    
    request_id = str(uuid.uuid4())[:8]
    
    try:
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Starting Lambda execution")
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Event keys: {list(event.keys())}")
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Context: {context}")
        

        
        function_name = event.get('function', '')
        parameters = event.get('parameters', [])
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Function name: '{function_name}' (type: {type(function_name)})")
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Parameters count: {len(parameters)}")
        
        # Log the entire event for debugging
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Full event: {json.dumps(event, indent=2)}")
        
        # Convert parameters to dict with proper array handling
        params = {}
        for param in parameters:
            if isinstance(param, dict) and 'name' in param and 'value' in param:
                value = param['value']
                param_name = param['name']
                
                logger.info(f"LAMBDA_HANDLER [{request_id}]: Processing param '{param_name}' = {value} (type: {type(value)})")
                
                # Handle different value types
                if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                    # Handle array parameters that might be passed as JSON strings
                    try:
                        value = json.loads(value)
                        logger.info(f"LAMBDA_HANDLER [{request_id}]: Parsed JSON array for '{param_name}': {value}")
                    except json.JSONDecodeError:
                        logger.warning(f"LAMBDA_HANDLER [{request_id}]: Failed to parse JSON for '{param_name}', keeping as string")
                        pass  # Keep as string if not valid JSON
                elif isinstance(value, str) and ',' in value and param_name in ['rc_numbers', 'build_numbers', 'components', 'integ_test_build_numbers']:
                    # Handle comma-separated values for array parameters
                    value = [item.strip() for item in value.split(',') if item.strip()]
                    logger.info(f"LAMBDA_HANDLER [{request_id}]: Split comma-separated '{param_name}': {value}")
                elif isinstance(value, str) and param_name in ['rc_numbers', 'build_numbers', 'components', 'integ_test_build_numbers'] and value.strip():
                    # Single value for array parameter - convert to list
                    value = [value.strip()]
                    logger.info(f"LAMBDA_HANDLER [{request_id}]: Converted single value to array for '{param_name}': {value}")
                
                params[param_name] = value
        
        # Get agent_type from parameters if passed by the supervisor agent
        agent_type = params.get('agent_type')
        
        # If agent_type is not provided, infer it from the function name using exact mappings
        if not agent_type:
            # Integration Test Agent functions
            if function_name in ['get_integration_test_metrics', 'get_rc_build_mapping']:
                agent_type = 'integration-test'
                logger.info(f"Mapped function '{function_name}' to agent_type 'integration-test'")
            
            # Build Metrics Agent functions  
            elif function_name in ['get_build_metrics', 'resolve_components_from_builds']:
                agent_type = 'build-metrics'
                logger.info(f"Mapped function '{function_name}' to agent_type 'build-metrics'")
            
            # Release Metrics Agent functions
            elif function_name in ['get_release_metrics']:
                agent_type = 'release-metrics'
                logger.info(f"Mapped function '{function_name}' to agent_type 'release-metrics'")

            # Default fallback
            else:
                agent_type = 'integration-test'  # Default fallback
                logger.warning(f"Unknown function '{function_name}', using default agent_type: {agent_type}")
        
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Function: {function_name}, Agent: {agent_type}")
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Final params: {params}")
        logger.info(f"LAMBDA_HANDLER [{request_id}]: About to route to function handler")
        
        # Route based on function name
        if function_name == 'test_basic':
            result = {'status': 'success', 'message': 'Enhanced Lambda function is working', 'agent_type': agent_type}
        # Route to specific function handlers
        elif function_name in [
            # Integration Test Agent functions
            'get_integration_test_metrics',
            # Build Metrics Agent functions  
            'get_build_metrics',
            # Release Metrics Agent functions
            'get_release_metrics',
            # Deprecated but still supported
            'get_test_metrics', 'get_metrics'
        ]:
            logger.info(f"LAMBDA_HANDLER [{request_id}]: Calling handle_metrics_query for {function_name}")
            result = handle_metrics_query(agent_type, function_name, params, request_id)
            logger.info(f"LAMBDA_HANDLER [{request_id}]: handle_metrics_query completed, result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Handle component resolution (used by both Build and Release agents)
        elif function_name == 'resolve_components_from_builds':
            logger.info(f"LAMBDA_HANDLER [{request_id}]: Calling handle_component_resolution")
            result = handle_component_resolution(params)
        
        # Handle RC build mapping (used by Integration Test agent)
        elif function_name == 'get_rc_build_mapping':
            logger.info(f"LAMBDA_HANDLER [{request_id}]: Calling handle_rc_build_mapping")
            result = handle_rc_build_mapping(params)
        
        # Handle unknown functions
        elif not function_name:
            logger.info(f"LAMBDA_HANDLER [{request_id}]: No function name provided, calling handle_metrics_query with default")
            result = handle_metrics_query(agent_type, function_name, params, request_id)
        else:
            result = {'error': f'Unknown function: {function_name}'}
        
        logger.info(f"LAMBDA_HANDLER [{request_id}]: About to create response")
        response = create_response(event, result)
        logger.info(f"LAMBDA_HANDLER [{request_id}]: Response created successfully")
        return response
        
    except Exception as e:
        logger.error(f"LAMBDA_HANDLER [{request_id}]: Exception occurred: {e}")
        logger.error(f"LAMBDA_HANDLER [{request_id}]: Stack trace: {traceback.format_exc()}")
        return create_response(event, {'error': str(e), 'type': 'lambda_error'})