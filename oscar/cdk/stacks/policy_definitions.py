#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
Least-privilege policy definitions for OSCAR components.

This module defines granular IAM policies with resource-specific access
and principle of least privilege for all OSCAR components.
"""

import os
from typing import Dict, List
from aws_cdk import aws_iam as iam


class OscarPolicyDefinitions:
    """
    Centralized policy definitions for OSCAR components.
    
    This class provides least-privilege IAM policy statements for different
    OSCAR components with resource-specific access controls.
    """
    
    def __init__(self, account_id: str, region: str) -> None:
        """
        Initialize policy definitions.
        
        Args:
            account_id: AWS account ID
            region: AWS region
        """
        self.account_id = account_id
        self.region = region
    
    def get_bedrock_agent_policies(self) -> List[iam.PolicyStatement]:
        """
        Get least-privilege policies for Bedrock agents.
        
        Returns:
            List of IAM policy statements for Bedrock agents
        """
        return [
            # Lambda invocation for action groups
            iam.PolicyStatement(
                sid="InvokeActionGroupLambdas",
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account_id}:function:oscar-communication-handler",
                    f"arn:aws:lambda:{self.region}:{self.account_id}:function:oscar-jenkins-agent",
                    f"arn:aws:lambda:{self.region}:{self.account_id}:function:oscar-*-metrics-agent*"
                ]
            ),
            
            # Knowledge Base retrieval
            iam.PolicyStatement(
                sid="KnowledgeBaseRetrieval",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}:{self.account_id}:knowledge-base/oscar-*"
                ]
            ),
            
            # Foundation model access
            iam.PolicyStatement(
                sid="FoundationModelAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-*",
                    f"arn:aws:bedrock:{self.region}:{self.account_id}:inference-profile/us.anthropic.claude-*"
                ]
            )
        ]
    
    def get_lambda_base_policies(self) -> List[iam.PolicyStatement]:
        """
        Get base policies for Lambda functions.
        
        Returns:
            List of IAM policy statements for base Lambda functions
        """
        return [
            # DynamoDB access for sessions and context
            iam.PolicyStatement(
                sid="DynamoDBSessionsAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/oscar-sessions*"
                ],
                conditions={
                    "ForAllValues:StringEquals": {
                        "dynamodb:Attributes": ["event_id", "ttl", "session_data"]
                    }
                }
            ),
            
            iam.PolicyStatement(
                sid="DynamoDBContextAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/oscar-context*"
                ],
                conditions={
                    "ForAllValues:StringEquals": {
                        "dynamodb:Attributes": ["thread_key", "ttl", "context_data", "user_id"]
                    }
                }
            ),
            
            # Secrets Manager access for central environment
            iam.PolicyStatement(
                sid="CentralSecretsAccess",
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:oscar-central-env-*"
                ]
            ),
            
            # Bedrock agent invocation
            iam.PolicyStatement(
                sid="BedrockAgentInvocation",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeAgent"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}:{self.account_id}:agent/oscar-*"
                ]
            ),
            
            # Bedrock model access for direct invocation
            iam.PolicyStatement(
                sid="BedrockModelInvocation",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-haiku-*",
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-*"
                ]
            ),
            
            # Lambda self-invocation for async processing
            iam.PolicyStatement(
                sid="LambdaSelfInvocation",
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account_id}:function:oscar-supervisor-agent-cdk",
                    f"arn:aws:lambda:{self.region}:{self.account_id}:function:oscar-communication-handler-cdk"
                ]
            )
        ]
    
    def get_vpc_lambda_policies(self) -> List[iam.PolicyStatement]:
        """
        Get policies for VPC Lambda functions (metrics agents).
        
        Returns:
            List of IAM policy statements for VPC Lambda functions
        """
        return [
            # Cross-account OpenSearch access
            iam.PolicyStatement(
                sid="CrossAccountOpenSearchAssumeRole",
                effect=iam.Effect.ALLOW,
                actions=["sts:AssumeRole"],
                resources=[os.environ.get("METRICS_CROSS_ACCOUNT_ROLE_ARN", "arn:aws:iam::979020455945:role/OpenSearchOscarAccessRole")],
                conditions={
                    "StringEquals": {
                        "sts:ExternalId": "oscar-metrics-access"
                    }
                }
            ),
            
            # Secrets Manager access for environment and credentials
            iam.PolicyStatement(
                sid="MetricsSecretsAccess",
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:oscar-central-env-*"
                ]
            ),
            
            # VPC endpoint access for S3 and DynamoDB
            iam.PolicyStatement(
                sid="VPCEndpointAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                resources=[
                    f"arn:aws:s3:::oscar-metrics-cache-{self.account_id}/*"
                ]
            )
        ]
    
    def get_communication_handler_policies(self) -> List[iam.PolicyStatement]:
        """
        Get policies for communication handler Lambda.
        
        Returns:
            List of IAM policy statements for communication handler
        """
        return [
            # DynamoDB access for message routing and context
            iam.PolicyStatement(
                sid="MessageRoutingDynamoDBAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query"
                ],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/oscar-sessions*",
                    f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/oscar-context*"
                ]
            ),
            
            # Secrets Manager access for Slack credentials
            iam.PolicyStatement(
                sid="SlackSecretsAccess",
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:oscar-central-env-*"
                ]
            ),
            
            # Lambda invocation for other OSCAR functions
            iam.PolicyStatement(
                sid="InvokeOscarLambdas",
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account_id}:function:oscar-supervisor-agent"
                ]
            )
        ]
    
    def get_jenkins_lambda_policies(self) -> List[iam.PolicyStatement]:
        """
        Get policies for Jenkins Lambda function.
        
        Returns:
            List of IAM policy statements for Jenkins Lambda
        """
        return [
            # Secrets Manager access for Jenkins API token
            iam.PolicyStatement(
                sid="JenkinsSecretsAccess",
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:oscar-central-env-*"
                ]
            ),
            
            # CloudWatch Logs for Jenkins job monitoring
            iam.PolicyStatement(
                sid="JenkinsLogsAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/lambda/oscar-jenkins-*"
                ]
            )
        ]
    
    def get_api_gateway_policies(self) -> List[iam.PolicyStatement]:
        """
        Get policies for API Gateway.
        
        Returns:
            List of IAM policy statements for API Gateway
        """
        return [
            # Lambda invocation for Slack webhooks
            iam.PolicyStatement(
                sid="SlackWebhookLambdaInvocation",
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{self.region}:{self.account_id}:function:oscar-supervisor-agent",
                    f"arn:aws:lambda:{self.region}:{self.account_id}:function:oscar-communication-handler"
                ]
            ),
            
            # CloudWatch Logs for API Gateway
            iam.PolicyStatement(
                sid="ApiGatewayLogsAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams"
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account_id}:log-group:/aws/apigateway/oscar-*"
                ]
            )
        ]
    
    def get_secrets_manager_policies(self) -> Dict[str, List[iam.PolicyStatement]]:
        """
        Get resource-specific Secrets Manager policies.
        
        Returns:
            Dictionary of Secrets Manager policies by resource type
        """
        return {
            "central_env": [
                iam.PolicyStatement(
                    sid="CentralEnvironmentSecretAccess",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret"
                    ],
                    resources=[
                        f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:oscar-central-env-*"
                    ]
                )
            ],
            

        }
    
    def get_dynamodb_resource_policies(self) -> Dict[str, List[iam.PolicyStatement]]:
        """
        Get resource-specific DynamoDB policies.
        
        Returns:
            Dictionary of DynamoDB policies by table type
        """
        return {
            "sessions_table": [
                iam.PolicyStatement(
                    sid="SessionsTableAccess",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem"
                    ],
                    resources=[
                        f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/oscar-sessions*"
                    ],
                    conditions={
                        "ForAllValues:StringEquals": {
                            "dynamodb:Attributes": ["event_id", "ttl", "session_data", "user_id"]
                        }
                    }
                )
            ],
            
            "context_table": [
                iam.PolicyStatement(
                    sid="ContextTableAccess",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:Query"
                    ],
                    resources=[
                        f"arn:aws:dynamodb:{self.region}:{self.account_id}:table/oscar-context*"
                    ],
                    conditions={
                        "ForAllValues:StringEquals": {
                            "dynamodb:Attributes": ["thread_key", "ttl", "context_data", "message_history"]
                        }
                    }
                )
            ]
        }
    
    def get_bedrock_service_policies(self) -> List[iam.PolicyStatement]:
        """
        Get Bedrock service policies with resource constraints.
        
        Returns:
            List of IAM policy statements for Bedrock services
        """
        return [
            # Agent management (read-only for monitoring)
            iam.PolicyStatement(
                sid="BedrockAgentReadAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:GetAgent",
                    "bedrock:ListAgents",
                    "bedrock:GetAgentAlias"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}:{self.account_id}:agent/oscar-*",
                    f"arn:aws:bedrock:{self.region}:{self.account_id}:agent-alias/oscar-*"
                ]
            ),
            
            # Knowledge Base access (read-only for monitoring)
            iam.PolicyStatement(
                sid="BedrockKnowledgeBaseReadAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:GetKnowledgeBase",
                    "bedrock:ListKnowledgeBases"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}:{self.account_id}:knowledge-base/oscar-*"
                ]
            ),
            
            # Model invocation with specific models only
            iam.PolicyStatement(
                sid="BedrockModelInvocationRestricted",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
                    f"arn:aws:bedrock:{self.region}:{self.account_id}:inference-profile/us.anthropic.claude-*"
                ]
            )
        ]