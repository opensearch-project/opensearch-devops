#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Enhanced Agent Module for OSCAR Agent.

This module provides the main agent class and interface definition,
coordinating all other components to provide the complete OSCAR agent functionality.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from bedrock.agent_invoker import BedrockAgentCore
from bedrock.error_handler import AgentErrorHandler
from bedrock.query_processor import QueryProcessor

logger = logging.getLogger(__name__)


class OSCARAgentInterface(ABC):
    """Abstract base class for OSCAR agent implementations.
    
    This interface defines the contract for all OSCAR agent implementations,
    ensuring consistent behavior across different agent types.
    """
    
    @abstractmethod
    def query(
        self, 
        query: str, 
        session_id: Optional[str] = None, 
        context_summary: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """Query the OSCAR agent with automatic routing.
        
        Args:
            query: The user's query to the agent
            session_id: Optional session ID for maintaining conversation context
            context_summary: Optional summary of previous conversation context
            
        Returns:
            Tuple containing (response_text, session_id)
        """


class EnhancedBedrockOSCARAgent(OSCARAgentInterface):
    """Enhanced Bedrock agent implementation for OSCAR with comprehensive capabilities.
    
    This class provides a robust interface to Amazon Bedrock agents with features:
    - Knowledge base integration for documentation queries
    - Metrics coordination through specialized Lambda functions
    - Automatic retry logic with exponential backoff
    - Session management and context preservation
    - Comprehensive error handling and user-friendly messages
    - Streaming response processing
    """
    
    def __init__(self, region: Optional[str] = None) -> None:
        """Initialize Enhanced Bedrock OSCAR agent.
        
        Args:
            region: AWS region for Bedrock service, defaults to config value
        """
        # Initialize all components
        self.bedrock_agent = BedrockAgentCore(region)
        self.error_handler = AgentErrorHandler()
        self.query_processor = QueryProcessor(self.bedrock_agent, self.error_handler)
        
        logger.info(f"Initialized EnhancedBedrockOSCARAgent with region: {self.bedrock_agent.region}")
    
    def query(
        self, 
        query: str, 
        privilege: bool,
        session_id: Optional[str] = None, 
        context_summary: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Query the enhanced OSCAR agent with automatic routing and coordination.
        
        This method provides intelligent routing between knowledge base queries
        and metrics analysis, with the supervisor agent coordinating responses.
        
        Args:
            query: The user's query to the agent
            session_id: Optional session ID for maintaining conversation context
            context_summary: Optional summary of previous conversation context
            
        Returns:
            A tuple containing (response_text, session_id)
        """
        return self.query_processor.process_query(query, privilege, session_id, context_summary)


def get_oscar_agent(region: Optional[str] = None) -> OSCARAgentInterface:
    """
    Get Enhanced OSCAR agent implementation.
    
    Args:
        region: AWS region for Bedrock service, defaults to config value if None
        
    Returns:
        An implementation of OSCARAgentInterface with enhanced capabilities
    """
    return EnhancedBedrockOSCARAgent(region)