#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
OSCAR Agent Lambda Handler.

Main AWS Lambda handler for OSCAR (OpenSearch Conversational Automation for Release).
This module handles Slack events, processes them asynchronously, and coordinates
between Slack, Bedrock agents, and DynamoDB storage.

Functions:
    lambda_handler: Main AWS Lambda entry point
    process_slack_event: Async Slack event processor
    get_event_id: Generate unique event identifiers
"""

import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
import slack_bolt

from config import config
from bedrock import get_oscar_agent
from slack_handler import SlackHandler
from context_storage import get_storage



logger = logging.getLogger()
logger.setLevel(logging.INFO)



# Initialize Slack app with process_before_response=True for immediate ack
app = App(
    token=config.slack_bot_token,
    signing_secret=config.slack_signing_secret,
    process_before_response=True
)

# Initialize storage and OSCAR agent
storage_instance = get_storage()
oscar_agent = get_oscar_agent()

# Initialize and register Slack handler
handler = SlackHandler(app, storage_instance, oscar_agent)
handler.register_handlers()

# Initialize Lambda client for async processing
lambda_client = boto3.client('lambda')
FUNCTION_NAME = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'oscar-supervisor-agent')



def process_slack_event(event: Dict[str, Any], context: Optional[object]) -> Dict[str, Any]:
    """
    Process a Slack event asynchronously.
    
    Args:
        event: The Slack event to process
        context: The Lambda context object
        
    Returns:
        Processing result
    """
    logger.info("Processing Slack event asynchronously with OSCAR agent")
    
    # Set the Lambda request ID for config caching
    if context and hasattr(context, 'aws_request_id'):
        config.set_request_id(context.aws_request_id)
    
    try:
        # Handle the Slack event
        slack_handler = SlackRequestHandler(app=app)
        result = slack_handler.handle(event, context)
        logger.info("Successfully processed Slack event with OSCAR agent")
        return result
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }



def lambda_handler(event: Dict[str, Any], context: Optional[object]) -> Dict[str, Any]:
    """
    AWS Lambda handler for Slack events and Bedrock action groups using OSCAR agent.
    
    Uses async processing pattern from old codebase to prevent duplicate responses.
    
    Args:
        event: The event dict from API Gateway, Bedrock, or direct Lambda invocation
        context: The Lambda context object
        
    Returns:
        API Gateway response object or processing result
    """
    logger.info("Received event for OSCAR agent processing")
    
    # Set the Lambda request ID for config caching
    if context and hasattr(context, 'aws_request_id'):
        config.set_request_id(context.aws_request_id)
    

    
    # Check if this is an async processing event
    if event.get('detail_type') == 'process_slack_event':
        logger.info("Processing async Slack event with OSCAR agent")
        return process_slack_event(event['detail'], context)
    
    # Extract event body for processing
    body = None
    if event.get('body') and event['body'].strip():  # Check if body exists and is not empty/whitespace
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse event body as JSON: {e}. Body: {event.get('body')[:100]}...")
            # For slash commands and other non-JSON payloads, continue without body parsing
            body = None
    
    # Handle Slack URL verification challenge immediately
    if body and body.get('type') == 'url_verification':
        challenge = body.get('challenge')
        logger.info(f"URL verification challenge: {challenge}")
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'challenge': challenge})
        }
    
    # Handle Slack retries - acknowledge but don't process --> implemented as such to avoid potential duplicate response issues
    if event.get('headers') and event.get('headers').get('X-Slack-Retry-Num'):
        retry_count = int(event.get('headers').get('X-Slack-Retry-Num', '0'))
        retry_reason = event.get('headers').get('X-Slack-Retry-Reason', 'unknown')
        logger.warning(f"Received retry request from Slack. Count: {retry_count}, Reason: {retry_reason}")
        
        # Always acknowledge retries without processing
        logger.warning(f"Acknowledging retry request without processing")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Retry acknowledged without processing'})
        }
    
    # For all other events, immediately acknowledge and then process asynchronously
    try:
        # Invoke this Lambda function asynchronously to process the event
        if FUNCTION_NAME:
            logger.info(f"Invoking Lambda function {FUNCTION_NAME} asynchronously for OSCAR agent processing")
            
            # Create payload for async processing
            payload = {
                'detail_type': 'process_slack_event',
                'detail': event
            }
            
            # Invoke Lambda asynchronously
            lambda_client.invoke(
                FunctionName=FUNCTION_NAME,
                InvocationType='Event',  # Asynchronous invocation
                Payload=json.dumps(payload)
            )
            
            logger.info("Successfully invoked async processing for OSCAR agent")
        else:
            logger.warning("Function name not available, cannot invoke async processing")
    
    except Exception as e:
        logger.error(f"Error invoking async processing: {e}", exc_info=True)
    
    # Always return 200 OK immediately to acknowledge the event
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Event received and will be processed asynchronously by OSCAR agent'})
    }