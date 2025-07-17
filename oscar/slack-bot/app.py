#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
OSCAR - OpenSearch Conversational Automation for Release 

Lambda handler for Slack events.
"""

import logging
import json
import boto3
import os
import time
import hashlib
from typing import Dict, Any, Optional

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from config import config
from storage import get_storage
from bedrock import get_knowledge_base
from slack_handler import SlackHandler

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Slack app with credentials from config
app = App(
    token=config.slack_bot_token,
    signing_secret=config.slack_signing_secret,
    process_before_response=True
)

# Initialize storage and knowledge base
storage_instance = get_storage()
knowledge_base = get_knowledge_base()

# Initialize and register Slack handler
handler = SlackHandler(app, storage_instance, knowledge_base)
handler.register_handlers()

# Initialize AWS Lambda client for async invocation
lambda_client = boto3.client('lambda')
FUNCTION_NAME = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'oscar-slack-bot')

def get_event_id(event: Dict[str, Any]) -> str:
    """
    Generate a unique ID for a Slack event.
    
    Args:
        event: The event dict from API Gateway
        
    Returns:
        A unique ID for the event
    """
    body = None
    if event.get('body'):
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
    
    # If this is a Slack event, use the event ID
    if body and body.get('event'):
        slack_event = body.get('event')
        event_ts = slack_event.get('event_ts') or slack_event.get('ts')
        channel = slack_event.get('channel')
        
        if event_ts and channel:
            return f"slack_event_{channel}_{event_ts}"
    
    # Fallback to request timestamp and signature
    if event.get('headers'):
        request_timestamp = event.get('headers').get('X-Slack-Request-Timestamp')
        request_signature = event.get('headers').get('X-Slack-Signature')
        
        if request_timestamp and request_signature:
            return f"slack_request_{request_timestamp}_{request_signature[-8:]}"
    
    # Last resort: use a hash of the entire event
    event_str = json.dumps(event, sort_keys=True)
    return f"event_hash_{hashlib.md5(event_str.encode()).hexdigest()}"

def process_slack_event(event: Dict[str, Any], context: Optional[object]) -> Dict[str, Any]:
    """
    Process a Slack event asynchronously.
    
    Args:
        event: The Slack event to process
        context: The Lambda context object
        
    Returns:
        Processing result
    """
    logger.info("Processing Slack event asynchronously")
    
    try:
        # Handle the Slack event
        slack_handler = SlackRequestHandler(app=app)
        result = slack_handler.handle(event, context)
        logger.info("Successfully processed Slack event")
        return result
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def lambda_handler(event: Dict[str, Any], context: Optional[object]) -> Dict[str, Any]:
    """
    AWS Lambda handler for Slack events.
    
    This function immediately acknowledges Slack events and then asynchronously
    processes them to prevent duplicate responses.
    
    Args:
        event: The event dict from API Gateway or direct Lambda invocation
        context: The Lambda context object
        
    Returns:
        API Gateway response object or processing result
    """
    logger.info("Received event")
    
    # Check if this is an async processing event
    if event.get('detail_type') == 'process_slack_event':
        logger.info("Processing async Slack event")
        return process_slack_event(event['detail'], context)
    
    # Log request ID for tracing
    request_id = context.aws_request_id if context and hasattr(context, 'aws_request_id') else 'unknown'
    logger.info(f"Lambda request ID: {request_id}")
    
    # Extract event body for processing
    body = None
    if event.get('body'):
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
    
    # Handle URL verification challenge immediately
    if body and body.get('type') == 'url_verification':
        logger.info("Received URL verification challenge")
        return {
            'statusCode': 200,
            'body': json.dumps({'challenge': body['challenge']})
        }
    
    # Handle Slack retries - acknowledge but don't process
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
            logger.info(f"Invoking Lambda function {FUNCTION_NAME} asynchronously")
            
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
            
            logger.info("Successfully invoked async processing")
        else:
            logger.warning("Function name not available, cannot invoke async processing")
    
    except Exception as e:
        logger.error(f"Error invoking async processing: {e}", exc_info=True)
    
    # Always return 200 OK immediately to acknowledge the event
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Event received and will be processed asynchronously'})
    }