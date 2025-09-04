#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Lambda function for handling automatic Knowledge Base document synchronization.

This function is triggered by S3 events when documents are added or updated
in the Knowledge Base documents bucket, and automatically triggers a
Knowledge Base sync job.
"""

import json
import logging
import os
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_agent_client = boto3.client('bedrock-agent')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle S3 events and trigger Knowledge Base synchronization.
    
    Args:
        event: Lambda event containing S3 event information
        context: Lambda context object
        
    Returns:
        Response dictionary with status information
    """
    try:
        # Get configuration from environment variables
        knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')
        data_source_id = os.environ.get('DATA_SOURCE_ID')
        
        if not knowledge_base_id or not data_source_id:
            raise ValueError("KNOWLEDGE_BASE_ID and DATA_SOURCE_ID environment variables are required")
        
        logger.info(f"Processing S3 event for Knowledge Base: {knowledge_base_id}")
        
        # Process S3 events
        processed_events = []
        sync_triggered = False
        
        for record in event.get('Records', []):
            if record.get('eventSource') == 'aws:s3':
                event_info = process_s3_event(record)
                processed_events.append(event_info)
                
                # Check if this is a document that should trigger sync
                if should_trigger_sync(event_info):
                    if not sync_triggered:
                        sync_job_id = trigger_knowledge_base_sync(knowledge_base_id, data_source_id)
                        sync_triggered = True
                        logger.info(f"Knowledge Base sync triggered. Job ID: {sync_job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'S3 events processed successfully',
                'processed_events': len(processed_events),
                'sync_triggered': sync_triggered,
                'events': processed_events
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing S3 events: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process S3 events'
            })
        }


def process_s3_event(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single S3 event record.
    
    Args:
        record: S3 event record
        
    Returns:
        Dictionary with processed event information
    """
    s3_info = record.get('s3', {})
    bucket_name = s3_info.get('bucket', {}).get('name', '')
    object_key = s3_info.get('object', {}).get('key', '')
    event_name = record.get('eventName', '')
    
    logger.info(f"S3 Event: {event_name} for {bucket_name}/{object_key}")
    
    return {
        'event_name': event_name,
        'bucket': bucket_name,
        'object_key': object_key,
        'event_time': record.get('eventTime', ''),
        'size': s3_info.get('object', {}).get('size', 0)
    }


def should_trigger_sync(event_info: Dict[str, Any]) -> bool:
    """
    Determine if an S3 event should trigger Knowledge Base synchronization.
    
    Args:
        event_info: Processed S3 event information
        
    Returns:
        True if sync should be triggered, False otherwise
    """
    # Only trigger sync for document files in the docs/ prefix
    object_key = event_info.get('object_key', '')
    event_name = event_info.get('event_name', '')
    
    # Check if it's in the docs/ prefix
    if not object_key.startswith('docs/'):
        logger.info(f"Skipping sync for non-docs object: {object_key}")
        return False
    
    # Check if it's a supported document type
    supported_extensions = {'.md', '.txt', '.rst', '.json'}
    file_extension = '.' + object_key.split('.')[-1].lower() if '.' in object_key else ''
    
    if file_extension not in supported_extensions:
        logger.info(f"Skipping sync for unsupported file type: {object_key}")
        return False
    
    # Check if it's a create or update event
    if not (event_name.startswith('ObjectCreated') or event_name.startswith('ObjectRemoved')):
        logger.info(f"Skipping sync for event type: {event_name}")
        return False
    
    logger.info(f"Sync will be triggered for: {object_key}")
    return True


def trigger_knowledge_base_sync(knowledge_base_id: str, data_source_id: str) -> str:
    """
    Trigger Knowledge Base synchronization.
    
    Args:
        knowledge_base_id: ID of the Knowledge Base
        data_source_id: ID of the data source
        
    Returns:
        Job ID of the triggered sync job
        
    Raises:
        ClientError: If the sync job fails to start
    """
    try:
        response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            description="Automatic sync triggered by S3 document update"
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"Knowledge Base sync job started: {job_id}")
        
        return job_id
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        # Handle specific error cases
        if error_code == 'ConflictException':
            logger.warning("Sync job already in progress, skipping trigger")
            return "already_in_progress"
        elif error_code == 'ThrottlingException':
            logger.warning("Sync job throttled, will retry later")
            raise
        else:
            logger.error(f"Failed to trigger sync job: {error_code} - {error_message}")
            raise
    
    except Exception as e:
        logger.error(f"Unexpected error triggering sync job: {str(e)}")
        raise


def get_sync_job_status(knowledge_base_id: str, data_source_id: str) -> Dict[str, Any]:
    """
    Get the status of the latest sync job.
    
    Args:
        knowledge_base_id: ID of the Knowledge Base
        data_source_id: ID of the data source
        
    Returns:
        Dictionary with sync job status information
    """
    try:
        response = bedrock_agent_client.list_ingestion_jobs(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            maxResults=1
        )
        
        if response['ingestionJobSummaries']:
            latest_job = response['ingestionJobSummaries'][0]
            return {
                'job_id': latest_job['ingestionJobId'],
                'status': latest_job['status'],
                'started_at': str(latest_job['startedAt']),
                'updated_at': str(latest_job.get('updatedAt', 'N/A'))
            }
        else:
            return {'status': 'No sync jobs found'}
            
    except Exception as e:
        logger.error(f"Failed to get sync job status: {str(e)}")
        return {'status': 'Error', 'error': str(e)}