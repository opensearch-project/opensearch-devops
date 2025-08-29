#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Slack Event Handler for OSCAR Agent.

This module provides comprehensive Slack event handling with agent integration,
including message processing, reaction management, and context preservation.

Classes:
    SlackHandler: Main handler for Slack events with agent integration
"""

# Import the refactored SlackHandler from the new modular structure
from slack_handler.slack_handler import SlackHandler

# Re-export for backward compatibility
__all__ = ['SlackHandler']