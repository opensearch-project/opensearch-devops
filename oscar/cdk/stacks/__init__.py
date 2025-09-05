#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
"""
OSCAR CDK stacks package.

This package contains the CDK stacks for deploying the complete OSCAR infrastructure.
"""

from .permissions_stack import OscarPermissionsStack
from .secrets_stack import OscarSecretsStack
from .storage_stack import OscarStorageStack
from .vpc_stack import OscarVpcStack
from .api_gateway_stack import OscarApiGatewayStack
from .knowledge_base_stack import OscarKnowledgeBaseStack
from .lambda_stack import OscarLambdaStack
from .bedrock_agents_stack import OscarAgentsStack

__all__ = [
    'OscarPermissionsStack',
    'OscarSecretsStack',
    'OscarStorageStack',
    'OscarVpcStack',
    'OscarApiGatewayStack',
    'OscarKnowledgeBaseStack',
    'OscarLambdaStack',
    'OscarAgentsStack'
]

__version__ = '1.0.0'