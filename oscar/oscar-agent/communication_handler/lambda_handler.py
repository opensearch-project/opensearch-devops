#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Lambda handler for Communication Handler.
"""

import json
import logging
from typing import Any, Dict

from message_handler import MessageHandler
from response_builder import ResponseBuilder

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for communication orchestration functionality.
    
    Args:
        event: Lambda event containing the action group request
        context: Lambda context
        
    Returns:
        Response for the Bedrock agent
    """
    try:

        
        logger.info(f"Received event: {json.dumps(event, indent=2)}")
        
        # Extract parameters from the event
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        function_name = event.get('function', '')
        parameters = event.get('parameters', [])
        
        # Convert parameters list to dictionary
        params = {}
        for param in parameters:
            params[param['name']] = param['value']
        
        logger.info(f"Processing action: {action_group}, path: {api_path}, params: {params}")
        
        # Initialize message handler
        message_handler = MessageHandler()
        response_builder = ResponseBuilder()
        
        # Handle the functions
        if function_name == 'send_automated_message':
            logger.info(f"Calling handle_send_message with params: {params}")
            return message_handler.handle_send_message(params, action_group, function_name)
        else:
            logger.error(f"Unknown function: {function_name}")
            return response_builder.create_error_response(action_group, function_name,
                f'Unknown function: {function_name}'
            )
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        logger.error(f"Full event: {json.dumps(event, indent=2)}")
        
        response_builder = ResponseBuilder()
        return response_builder.create_error_response(action_group, function_name,
            f'Internal server error: {str(e)}'
        )
