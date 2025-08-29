#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Query Processor Module for OSCAR Agent.

This module handles query routing, context management, and the multi-attempt
query strategy for the OSCAR agent system.
"""

import logging
from typing import Optional, Tuple

from config import config
from bedrock.agent_invoker import BedrockAgentCore
from bedrock.error_handler import AgentErrorHandler

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Processes queries with intelligent routing and context management."""
    
    def __init__(self, bedrock_agent: BedrockAgentCore, error_handler: AgentErrorHandler) -> None:
        """
        Initialize the query processor.
        
        Args:
            bedrock_agent: The Bedrock agent core instance
            error_handler: The error handler instance
        """
        self.bedrock_agent = bedrock_agent
        self.error_handler = error_handler
        
        logger.info("Initialized QueryProcessor")
    
    def process_query(
        self, 
        query: str, 
        privilege: bool,
        session_id: Optional[str] = None, 
        context_summary: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Process a query with intelligent routing and context management.
        
        This method implements a multi-attempt strategy:
        1. Try with session_id if available (with context if provided)
        2. Try with context summary but no session_id
        3. Try with plain query as fallback
        
        Args:
            query: The user's query to the agent
            session_id: Optional session ID for maintaining conversation context
            context_summary: Optional summary of previous conversation context
            
        Returns:
            A tuple containing (response_text, session_id)
        """
        logger.info(f"AGENT_QUERY: Starting query - query_len={len(query)}, session_id='{session_id}', context_len={len(context_summary) if context_summary else 0}")
        logger.info(f"AGENT_QUERY: Query preview: {query[:config.log_query_preview_length]}...")
        
        # Store original session ID for context preservation
        original_session_id = session_id
        
        # The supervisor agent handles all routing internally through its
        # knowledge base integration and collaborator agents, so we just
        # need to invoke it directly
        
        # First attempt: Try with session_id if available
        if session_id:
            try:
                # Check if we also have context_summary - if so, use enhanced query WITH session_id
                if context_summary and context_summary.strip():
                    enhanced_query = f"Previous conversation context:\n{context_summary}\n\nCurrent question: {query}"
                    logger.info(f"AGENT_QUERY: Attempting enhanced query WITH session_id: {session_id}, context_len={len(context_summary)}")
                    logger.info(f"AGENT_QUERY: Enhanced query length: {len(enhanced_query)} characters")
                    response, returned_session_id = self.bedrock_agent.invoke_agent(enhanced_query, privilege, session_id)
                else:
                    # No context available, use plain query with session_id
                    logger.info(f"AGENT_QUERY: Attempting plain query with session_id: {session_id} (no context available)")
                    response, returned_session_id = self.bedrock_agent.invoke_agent(query, privilege, session_id)
                
                # Ensure we return the session ID (either returned or original)
                final_session_id = returned_session_id or session_id
                logger.info(f"AGENT_QUERY: Session-based query succeeded with session_id: {final_session_id}")
                logger.info(f"AGENT_QUERY: Response length: {len(response)} characters")
                return response, final_session_id
            except Exception as e:
                logger.warning(f"AGENT_QUERY: Session-based query failed (possibly expired session): {e}")
        
        # Second attempt: Use enhanced query with context summary (without session_id)
        if context_summary and context_summary.strip():  # Check for non-empty context
            logger.info(f"AGENT_QUERY: Using context-enhanced query without session_id, context_len={len(context_summary)}")
            enhanced_query = f"Previous conversation context:\n{context_summary}\n\nCurrent question: {query}"
            logger.info(f"AGENT_QUERY: Enhanced query length: {len(enhanced_query)} characters")
            try:
                response, new_session_id = self.bedrock_agent.invoke_agent(enhanced_query, privilege, None)
                logger.info(f"AGENT_QUERY: Context-enhanced query succeeded with new session: {new_session_id}")
                logger.info(f"AGENT_QUERY: Response length: {len(response)} characters")
                return response, new_session_id
            except Exception as e:
                logger.warning(f"AGENT_QUERY: Context-enhanced query failed: {e}")
        else:
            logger.info(f"AGENT_QUERY: No context summary provided or empty context")
        
        # Third attempt: Just use the plain query as last resort
        logger.info("AGENT_QUERY: Using plain query without context or session")
        try:
            response, new_session_id = self.bedrock_agent.invoke_agent(query, privilege, None)
            logger.info(f"AGENT_QUERY: Plain query succeeded with new session: {new_session_id}")
            logger.info(f"AGENT_QUERY: Response length: {len(response)} characters")
            return response, new_session_id
        except Exception as e:
            logger.error(f"AGENT_QUERY: All query attempts failed: {e}", exc_info=True)
            error_message = self.error_handler.handle_agent_error(e, query)
            return error_message, original_session_id  # Return original session ID to preserve context