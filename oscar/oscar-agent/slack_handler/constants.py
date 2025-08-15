#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Constants for Slack Handler.

This module loads configuration from environment variables via the config module.
All magic numbers and hardcoded values have been moved to configuration.
"""

from config import config

# Load configuration from environment variables
CHANNEL_ALLOW_LIST = config.channel_allow_list
AUTHORIZED_MESSAGE_SENDERS = config.authorized_message_senders
HOURGLASS_THRESHOLD = config.hourglass_threshold
TIMEOUT_THRESHOLD = config.timeout_threshold
MAX_WORKERS = config.max_workers
MAX_ACTIVE_QUERIES = config.max_active_queries
AGENT_QUERIES = config.agent_queries