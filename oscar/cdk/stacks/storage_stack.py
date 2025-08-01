#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Storage stack for OSCAR Slack Bot.

This module defines the DynamoDB tables used by the OSCAR Slack Bot for persistent
data storage. It creates two tables:

1. Sessions Table: Stores session data with event_id as partition key
2. Context Table: Stores conversation context with thread_key as partition key

Both tables use:
- Pay-per-request billing for cost optimization
- TTL attributes for automatic data cleanup
- AWS-managed encryption for security
- Stage-appropriate removal policies
"""

import logging
import os
from typing import Optional
from aws_cdk import (
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    CfnOutput
)
from constructs import Construct

# Configure logging
logger = logging.getLogger(__name__)

# Default table names
DEFAULT_SESSIONS_TABLE = "oscar-sessions-v2"
DEFAULT_CONTEXT_TABLE = "oscar-context"

class OscarStorageStack(Construct):
    """
    Storage resources for OSCAR Slack Bot.
    
    Creates and configures DynamoDB tables for persistent data storage:
    - Sessions table for deduplication and session management
    - Context table for conversation history and context preservation
    
    Features:
    - Configurable table names via CDK context
    - Stage-appropriate removal policies (retain for Prod, destroy for Dev/Beta)
    - Pay-per-request billing for cost optimization
    - TTL attributes for automatic data cleanup
    - AWS-managed encryption
    """
    
    def __init__(self, scope: Construct, construct_id: str) -> None:
        """
        Initialize storage resources with configuration management.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
        """
        super().__init__(scope, construct_id)
        
        logger.info("Creating storage stack resources for %s", construct_id)
        
        # Get deployment configuration
        config = self._get_storage_configuration(scope)
        
        # Create DynamoDB tables with appropriate policies
        self.sessions_table = self._create_sessions_table(
            config['sessions_table_name'], 
            config['removal_policy']
        )
        self.context_table = self._create_context_table(
            config['context_table_name'], 
            config['removal_policy']
        )
        
        # Export table information for other stacks
        self._add_outputs()
        
        logger.info("Storage stack resources created successfully")
        logger.info("Sessions table: %s", self.sessions_table.table_name)
        logger.info("Context table: %s", self.context_table.table_name)
    
    def _get_storage_configuration(self, scope: Construct) -> dict:
        """
        Get storage configuration from context and environment.
        
        Args:
            scope: The CDK construct scope for context access
            
        Returns:
            Dictionary with storage configuration
        """
        app = scope.node.root
        stage = app.node.try_get_context('stage') or 'Dev'
        
        # Get table names with fallback hierarchy: context -> env -> default
        sessions_table_name = (
            app.node.try_get_context('sessions_table_name') or
            os.environ.get("SESSIONS_TABLE_NAME", DEFAULT_SESSIONS_TABLE)
        )
        
        context_table_name = (
            app.node.try_get_context('context_table_name') or
            os.environ.get("CONTEXT_TABLE_NAME", DEFAULT_CONTEXT_TABLE)
        )
        
        # Set removal policy based on stage (retain production data)
        removal_policy = (
            RemovalPolicy.RETAIN if stage == 'Prod' else RemovalPolicy.DESTROY
        )
        
        config = {
            'stage': stage,
            'sessions_table_name': sessions_table_name,
            'context_table_name': context_table_name,
            'removal_policy': removal_policy
        }
        
        logger.info("Storage configuration: %s", config)
        return config
    
    def _add_outputs(self) -> None:
        """Add CloudFormation outputs for table references."""
        CfnOutput(
            self, "SessionsTableName",
            value=self.sessions_table.table_name,
            description="Name of the DynamoDB table for session data",
            export_name=f"{self.node.scope.stack_name}-SessionsTableName"
        )
        
        CfnOutput(
            self, "ContextTableName", 
            value=self.context_table.table_name,
            description="Name of the DynamoDB table for context data",
            export_name=f"{self.node.scope.stack_name}-ContextTableName"
        )
    
    def _create_sessions_table(self, table_name: str, removal_policy: RemovalPolicy) -> dynamodb.Table:
        """
        Create DynamoDB table for session data and deduplication.
        
        The sessions table stores:
        - Event deduplication data (event_id as partition key)
        - Session state information
        - TTL for automatic cleanup
        
        Args:
            table_name: Name for the DynamoDB table
            removal_policy: CDK removal policy for the table
            
        Returns:
            Configured DynamoDB table for sessions
        """
        table = dynamodb.Table(
            self, "OscarSessionsTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="event_id",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=removal_policy == RemovalPolicy.RETAIN,  # Enable for production
            deletion_protection=removal_policy == RemovalPolicy.RETAIN,     # Protect production data
            table_class=dynamodb.TableClass.STANDARD
        )
        
        logger.info("Created sessions table: %s", table_name)
        return table
    
    def _create_context_table(self, table_name: str, removal_policy: RemovalPolicy) -> dynamodb.Table:
        """
        Create DynamoDB table for conversation context storage.
        
        The context table stores:
        - Conversation history (thread_key as partition key)
        - Context summaries and metadata
        - TTL for automatic cleanup
        
        Args:
            table_name: Name for the DynamoDB table
            removal_policy: CDK removal policy for the table
            
        Returns:
            Configured DynamoDB table for context
        """
        table = dynamodb.Table(
            self, "OscarContextTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="thread_key",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=removal_policy == RemovalPolicy.RETAIN,  # Enable for production
            deletion_protection=removal_policy == RemovalPolicy.RETAIN,     # Protect production data
            table_class=dynamodb.TableClass.STANDARD
        )
        
        logger.info("Created context table: %s", table_name)
        return table