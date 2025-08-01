#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.
"""
OSCAR CDK stacks package.

This package contains the CDK stacks for deploying the OSCAR Slack Bot infrastructure.
"""

from .slack_bot_stack import OscarSlackBotStack
from .storage_stack import OscarStorageStack
from .lambda_stack import OscarLambdaStack

__all__ = [
    'OscarSlackBotStack',
    'OscarStorageStack',
    'OscarLambdaStack'
]

# Package version
__version__ = '0.1.0'