#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Knowledge Base stack for OSCAR CDK automation.

This module defines the Knowledge Base infrastructure including S3 bucket for document storage,
OpenSearch Serverless collection for vector search, and Bedrock Knowledge Base with document
ingestion pipeline and vector embeddings using Titan.
"""

import os
from typing import Dict, List, Optional, Any
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    CustomResource,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_opensearchserverless as opensearchserverless,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    CfnOutput,

)
from constructs import Construct


class OscarKnowledgeBaseStack(Stack):
    """
    Knowledge Base infrastructure for OSCAR.
    
    This construct creates and configures the Knowledge Base infrastructure including:
    - S3 bucket for document storage with versioning and lifecycle policies
    - OpenSearch Serverless collection with vector search capabilities
    - Bedrock Knowledge Base with document ingestion pipeline
    - Vector embeddings using Titan and metadata extraction
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize Knowledge Base stack.
        
        Args:
            scope: The CDK construct scope
            construct_id: The ID of the construct
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Get configuration from environment
        self.account_id = os.environ.get("CDK_DEFAULT_ACCOUNT")
        self.aws_region = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
        self.env_name = os.environ.get("ENVIRONMENT", "dev")
        
        # Determine removal policy based on environment
        self.removal_policy = (
            RemovalPolicy.RETAIN if self.env_name == "prod" else RemovalPolicy.DESTROY
        )
        
        # Create S3 bucket for document storage
        self.documents_bucket = self._create_documents_bucket()
        
        # Create OpenSearch Serverless collection
        self.opensearch_collection = self._create_opensearch_collection()
        
        # Create Knowledge Base
        self.knowledge_base = self._create_knowledge_base()
        
        # Create data source for document ingestion
        self.data_source = self._create_data_source()
        
        # Create Lambda function for automatic document synchronization
        self.sync_lambda = self._create_document_sync_lambda()
        
        # Add S3 event notification for automatic sync
        self._configure_s3_notifications()
        
        # Create outputs
        self._create_outputs()
    
    def _create_documents_bucket(self) -> s3.Bucket:
        """
        Create S3 bucket for document storage with versioning and lifecycle policies.
        
        Returns:
            The S3 bucket for document storage
        """
        bucket = s3.Bucket(
            self, "OscarDocumentsBucket",
            bucket_name=f"oscar-knowledge-docs-cdk-created-{self.account_id}-{self.aws_region}",
            versioned=True,
            removal_policy=self.removal_policy,
            auto_delete_objects=self.removal_policy == RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    enabled=True,
                    noncurrent_version_expiration=Duration.days(90),
                    abort_incomplete_multipart_upload_after=Duration.days(7)
                ),
                s3.LifecycleRule(
                    id="TransitionToIA",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )
        
        # We'll add the S3 event notification after creating the Lambda function
        
        return bucket
    
    def _create_opensearch_collection(self) -> opensearchserverless.CfnCollection:
        """
        Create OpenSearch Serverless collection with vector search capabilities.
        
        Returns:
            The OpenSearch Serverless collection
        """
        # Create encryption policy (shortened name to fit 32 char limit)
        encryption_policy = opensearchserverless.CfnSecurityPolicy(
            self, "OscarKnowledgeBaseEncryptionPolicy",
            name=f"oscar-kb-encrypt-cdk-{self.env_name}",
            type="encryption",
            policy=f"""{{
                "Rules": [
                    {{
                        "ResourceType": "collection",
                        "Resource": ["collection/oscar-kb-cdk-{self.env_name}"]
                    }}
                ],
                "AWSOwnedKey": true
            }}"""
        )
        
        # Create network policy (shortened name to fit 32 char limit)
        network_policy = opensearchserverless.CfnSecurityPolicy(
            self, "OscarKnowledgeBaseNetworkPolicy",
            name=f"oscar-kb-network-cdk-{self.env_name}",
            type="network",
            policy=f"""[{{
                "Rules": [
                    {{
                        "ResourceType": "collection",
                        "Resource": ["collection/oscar-kb-cdk-{self.env_name}"]
                    }},
                    {{
                        "ResourceType": "dashboard",
                        "Resource": ["collection/oscar-kb-cdk-{self.env_name}"]
                    }}
                ],
                "AllowFromPublic": true
            }}]"""
        )
        
        # Create data access policy (shortened name to fit 32 char limit)
        # Note: We'll create this after the KB service role is created
        data_access_policy = None
        
        # Create the collection
        collection = opensearchserverless.CfnCollection(
            self, "OscarKnowledgeBaseCollection",
            name=f"oscar-kb-cdk-{self.env_name}",
            description="OpenSearch Serverless collection for OSCAR Knowledge Base vector search",
            type="VECTORSEARCH",
            standby_replicas="DISABLED"  # Cost optimization for non-prod
        )
        
        # Add dependencies
        collection.add_dependency(encryption_policy)
        collection.add_dependency(network_policy)
        
        return collection
    
    def _create_knowledge_base(self) -> bedrock.CfnKnowledgeBase:
        """
        Create Bedrock Knowledge Base with vector embeddings using Titan.
        
        Returns:
            The Bedrock Knowledge Base
        """
        # Create service role for Knowledge Base
        kb_service_role = iam.Role(
            self, "KnowledgeBaseServiceRole",
            role_name=f"AmazonBedrockExecutionRoleForKnowledgeBase-oscar-cdk-created-{self.env_name}",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Service role for OSCAR Bedrock Knowledge Base"
        )
        
        # Add permissions for S3 access
        kb_service_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3Access",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    self.documents_bucket.bucket_arn,
                    f"{self.documents_bucket.bucket_arn}/*"
                ]
            )
        )
        
        # Add permissions for OpenSearch Serverless access
        kb_service_role.add_to_policy(
            iam.PolicyStatement(
                sid="OpenSearchServerlessAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "aoss:APIAccessAll"
                ],
                resources=[
                    f"arn:aws:aoss:{self.aws_region}:{self.account_id}:collection/*"
                ]
            )
        )
        
        # Add permissions for Bedrock model access
        kb_service_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockModelAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.aws_region}::foundation-model/amazon.titan-embed-text-v1"
                ]
            )
        )
        
        # Create data access policy now that we have the service role ARN
        data_access_policy = opensearchserverless.CfnAccessPolicy(
            self, "OscarKnowledgeBaseDataAccessPolicy",
            name=f"oscar-kb-data-cdk-{self.env_name}",
            type="data",
            policy=f"""[{{
                "Rules": [
                    {{
                        "ResourceType": "collection",
                        "Resource": ["collection/oscar-kb-cdk-{self.env_name}"],
                        "Permission": [
                            "aoss:CreateCollectionItems",
                            "aoss:DeleteCollectionItems",
                            "aoss:UpdateCollectionItems",
                            "aoss:DescribeCollectionItems"
                        ]
                    }},
                    {{
                        "ResourceType": "index",
                        "Resource": ["index/oscar-kb-cdk-{self.env_name}/*"],
                        "Permission": [
                            "aoss:CreateIndex",
                            "aoss:DeleteIndex",
                            "aoss:UpdateIndex",
                            "aoss:DescribeIndex",
                            "aoss:ReadDocument",
                            "aoss:WriteDocument"
                        ]
                    }}
                ],
                "Principal": [
                    "arn:aws:iam::{self.account_id}:root",
                    "{kb_service_role.role_arn}"
                ]
            }}]"""
        )
        
        # Note: Bedrock will automatically create the vector index when the Knowledge Base is created
        # No need for custom bootstrap resource
        
        # Create the Knowledge Base
        knowledge_base = bedrock.CfnKnowledgeBase(
            self, "OscarKnowledgeBase",
            name=f"oscar-kb-cdk-{self.env_name}",
            description="OSCAR Knowledge Base for OpenSearch release management documentation",
            role_arn=kb_service_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=f"arn:aws:bedrock:{self.aws_region}::foundation-model/amazon.titan-embed-text-v1"
                )
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=self.opensearch_collection.attr_arn,
                    vector_index_name="bedrock-knowledge-base-default-index",
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        vector_field="bedrock-knowledge-base-default-vector",
                        text_field="AMAZON_BEDROCK_TEXT_CHUNK",
                        metadata_field="AMAZON_BEDROCK_METADATA"
                    )
                )
            )
        )
        
        # Add dependencies
        knowledge_base.add_dependency(self.opensearch_collection)
        knowledge_base.add_dependency(data_access_policy)
        
        return knowledge_base
    
    def _create_data_source(self) -> bedrock.CfnDataSource:
        """
        Create data source for document ingestion from S3.
        
        Returns:
            The Bedrock data source
        """
        data_source = bedrock.CfnDataSource(
            self, "OscarKnowledgeBaseDataSource",
            name=f"oscar-docs-data-source-cdk-created-{self.env_name}",
            description="Data source for OSCAR documentation ingestion",
            knowledge_base_id=self.knowledge_base.attr_knowledge_base_id,
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=self.documents_bucket.bucket_arn,
                    inclusion_prefixes=["docs/"],  # Only ingest from docs/ prefix
                )
            ),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="FIXED_SIZE",
                    fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                        max_tokens=300,
                        overlap_percentage=20
                    )
                )
            )
        )
        
        # Add dependency on knowledge base
        data_source.add_dependency(self.knowledge_base)
        
        return data_source
    
    def _create_document_sync_lambda(self) -> lambda_.Function:
        """
        Create Lambda function for automatic document synchronization.
        
        Returns:
            The Lambda function for document sync
        """
        # Create execution role for the Lambda function
        sync_lambda_role = iam.Role(
            self, "DocumentSyncLambdaRole",
            role_name=f"oscar-document-sync-lambda-role-cdk-created-{self.env_name}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
            description="Execution role for OSCAR document sync Lambda function"
        )
        
        # Add permissions for Bedrock agent operations
        sync_lambda_role.add_to_policy(
            iam.PolicyStatement(
                sid="BedrockAgentAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agent:StartIngestionJob",
                    "bedrock-agent:ListIngestionJobs",
                    "bedrock-agent:GetIngestionJob"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.aws_region}:{self.account_id}:knowledge-base/{self.knowledge_base.attr_knowledge_base_id}",
                    f"arn:aws:bedrock:{self.aws_region}:{self.account_id}:knowledge-base/{self.knowledge_base.attr_knowledge_base_id}/data-source/*"
                ]
            )
        )
        
        # Create the Lambda function
        sync_lambda = lambda_.Function(
            self, "DocumentSyncLambda",
            function_name=f"oscar-document-sync-cdk-created-{self.env_name}",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="document_sync_handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda"),
            role=sync_lambda_role,
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "KNOWLEDGE_BASE_ID": self.knowledge_base.attr_knowledge_base_id,
                "DATA_SOURCE_ID": self.data_source.attr_data_source_id,
                "LOG_LEVEL": "INFO"
            },
            description="Handles automatic Knowledge Base synchronization when documents are updated"
        )
        
        # Add dependency on data source
        sync_lambda.node.add_dependency(self.data_source)
        
        return sync_lambda
    

    
    def _configure_s3_notifications(self) -> None:
        """
        Configure S3 event notifications for automatic document synchronization.
        """
        # Add S3 event notifications for document changes
        self.documents_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.sync_lambda),
            s3.NotificationKeyFilter(prefix="docs/")
        )
        
        self.documents_bucket.add_event_notification(
            s3.EventType.OBJECT_REMOVED,
            s3n.LambdaDestination(self.sync_lambda),
            s3.NotificationKeyFilter(prefix="docs/")
        )
    
    def _create_outputs(self) -> None:
        """Create CloudFormation outputs for the Knowledge Base resources."""
        # S3 bucket outputs
        CfnOutput(
            self, "DocumentsBucketName",
            value=self.documents_bucket.bucket_name,
            description="Name of the S3 bucket for Knowledge Base documents"
        )
        
        CfnOutput(
            self, "DocumentsBucketArn",
            value=self.documents_bucket.bucket_arn,
            description="ARN of the S3 bucket for Knowledge Base documents"
        )
        
        # OpenSearch collection outputs
        CfnOutput(
            self, "OpenSearchCollectionArn",
            value=self.opensearch_collection.attr_arn,
            description="ARN of the OpenSearch Serverless collection"
        )
        
        CfnOutput(
            self, "OpenSearchCollectionEndpoint",
            value=self.opensearch_collection.attr_collection_endpoint,
            description="Endpoint of the OpenSearch Serverless collection"
        )
        
        # Knowledge Base outputs
        CfnOutput(
            self, "KnowledgeBaseId",
            value=self.knowledge_base.attr_knowledge_base_id,
            description="ID of the Bedrock Knowledge Base"
        )
        
        CfnOutput(
            self, "KnowledgeBaseArn",
            value=self.knowledge_base.attr_knowledge_base_arn,
            description="ARN of the Bedrock Knowledge Base"
        )
        
        # Data source outputs
        CfnOutput(
            self, "DataSourceId",
            value=self.data_source.attr_data_source_id,
            description="ID of the Knowledge Base data source"
        )
        
        # Lambda function outputs
        CfnOutput(
            self, "DocumentSyncLambdaArn",
            value=self.sync_lambda.function_arn,
            description="ARN of the document synchronization Lambda function"
        )
        
        CfnOutput(
            self, "DocumentSyncLambdaName",
            value=self.sync_lambda.function_name,
            description="Name of the document synchronization Lambda function"
        )