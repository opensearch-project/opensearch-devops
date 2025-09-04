#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Enhanced OSCAR Agent Integration Module.

This module provides the core Bedrock agent interface for OSCAR (OpenSearch 
Conversational Automation for Release). It handles agent invocation, session 
management, error handling, response processing, and coordinates between
knowledge base queries and metrics analysis.

Classes:
    OSCARAgentInterface: Abstract base class for agent implementations
    EnhancedBedrockOSCARAgent: Enhanced Bedrock agent with knowledge base + metrics coordination
Functions:
    get_oscar_agent: Factory function to get Enhanced OSCAR agent implementation
"""

# Import the refactored components from the new modular structure
from bedrock.main_agent import OSCARAgentInterface, EnhancedBedrockOSCARAgent, get_oscar_agent

# Re-export for backward compatibility
__all__ = ['OSCARAgentInterface', 'EnhancedBedrockOSCARAgent', 'get_oscar_agent']