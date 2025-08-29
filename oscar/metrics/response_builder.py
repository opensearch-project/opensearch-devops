#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Response Builder for Metrics Lambda Functions.

This module provides response building utilities for creating properly
formatted responses for the Bedrock agent system.

Functions:
    create_response: Create a response in the format expected by the Bedrock agent
"""

import json
import logging
from typing import Any, Dict

from config import config

logger = logging.getLogger(__name__)


def create_response(event: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Create a response in the format expected by the Bedrock agent."""
    logger.info(f"CREATE_RESPONSE: Starting response creation")
    action_group = event.get('actionGroup')
    function = event.get('function', 'unknown')
    logger.info(f"CREATE_RESPONSE: action_group={action_group}, function={function}")
    
    # Add data source information to response if not present
    if isinstance(result, dict) and 'data_source' in result:
        result['response_footer'] = f"\n\n*Data retrieved from {result['data_source']} index*"
    
    logger.info(f"CREATE_RESPONSE: About to serialize result to JSON")
    response_body_string = json.dumps(result, default=str)
    logger.info(f"CREATE_RESPONSE: JSON serialization complete, length: {len(response_body_string)}")

    final_response = {
        "messageVersion": config.bedrock_message_version,
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": response_body_string
                    }
                }
            }
        }
    }
    logger.info(f"CREATE_RESPONSE: Response creation complete")
    return final_response