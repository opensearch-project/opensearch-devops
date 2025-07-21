#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Storage stack for OSCAR Slack Bot.

This module defines the DynamoDB tables used by the OSCAR Slack Bot.
"""

import os
from typing import Optional
from aws_cdk import (
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    CfnOutput
)
from constructs import Construct

class OscarStorageStack(Construct):
    """
    Storage resources for OSCAR Slack Bot.
    
    This construct creates and configures the DynamoDB tables used by the
    OSCAR Slack Bot for storing session data and conversation context.
    """
    
    def __init__(self, scope: Construct, construct_id: str) -> None:
        """
        Initialize storage resources.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
        """
        super().__init__(scope, construct_id)
        
        # Get table names from environment variables or use defaults
        sessions_table_name: str = os.environ.get("SESSIONS_TABLE_NAME", "oscar-sessions-v2")
        context_table_name: str = os.environ.get("CONTEXT_TABLE_NAME", "oscar-context")
        
        # Determine removal policy based on environment
        environment: str = os.environ.get("ENVIRONMENT", "dev")
        removal_policy: RemovalPolicy = (
            RemovalPolicy.RETAIN if environment == "prod" else RemovalPolicy.DESTROY
        )
        
        # Create DynamoDB Tables
        self.sessions_table = self._create_sessions_table(
            sessions_table_name, 
            removal_policy
        )

        self.context_table = self._create_context_table(
            context_table_name, 
            removal_policy
        )
        
        # Outputs
        CfnOutput(
            self, "SessionsTableName",
            value=self.sessions_table.table_name,
            description="Name of the DynamoDB table for session data"
        )
        
        CfnOutput(
            self, "ContextTableName",
            value=self.context_table.table_name,
            description="Name of the DynamoDB table for context data"
        )
    
    def _create_sessions_table(
        self, 
        table_name: str, 
        removal_policy: RemovalPolicy
    ) -> dynamodb.Table:
        """
        Create the sessions DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            removal_policy: CDK removal policy for the table
            
        Returns:
            The created DynamoDB table
        """
        return dynamodb.Table(
            self, "OscarSessionsTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="event_id",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )
    
    def _create_context_table(
        self, 
        table_name: str, 
        removal_policy: RemovalPolicy
    ) -> dynamodb.Table:
        """
        Create the context DynamoDB table.
        
        Args:
            table_name: Name of the DynamoDB table
            removal_policy: CDK removal policy for the table
            
        Returns:
            The created DynamoDB table
        """
        return dynamodb.Table(
            self, "OscarContextTable",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name="thread_key",
                type=dynamodb.AttributeType.STRING
            ),
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )