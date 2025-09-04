#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Communication Handler for OSCAR Supervisor Agent.

This module provides the Lambda function handler for automated message sending
functionality integrated with the OSCAR supervisor agent.
"""

# Import the refactored lambda_handler from the new modular structure
from communication_handler.lambda_handler import lambda_handler

# Re-export for backward compatibility
__all__ = ['lambda_handler']