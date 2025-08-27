#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
OSCAR Agent Package - Modular implementation of the Enhanced Bedrock OSCAR Agent.

This package provides a modular structure for the OSCAR agent functionality,
split into focused components for better maintainability and testing.
"""

# Import main components for easy access
from bedrock.main_agent import OSCARAgentInterface, EnhancedBedrockOSCARAgent, get_oscar_agent

__all__ = ['OSCARAgentInterface', 'EnhancedBedrockOSCARAgent', 'get_oscar_agent']