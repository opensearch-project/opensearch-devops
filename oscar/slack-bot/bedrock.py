#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Bedrock integration module for OSCAR.

This module provides classes for interacting with Amazon Bedrock.
"""

import logging
import json
import boto3
from typing import Tuple, Optional, Dict, Any
from abc import ABC, abstractmethod

from config import config

# Configure logging
logger = logging.getLogger(__name__)

class KnowledgeBaseInterface(ABC):
    """Abstract base class for knowledge base implementations."""
    
    @abstractmethod
    def query(self, query: str, session_id: Optional[str] = None, 
              context_summary: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Query the knowledge base.
        
        Args:
            query: The user's query to the knowledge base
            session_id: Optional session ID for maintaining conversation context
            context_summary: Optional summary of previous conversation context
            
        Returns:
            A tuple containing (response_text, session_id)
        """
        pass

class BedrockKnowledgeBase(KnowledgeBaseInterface):
    """Amazon Bedrock implementation of knowledge base interface."""
    
    def __init__(self, region: Optional[str] = None) -> None:
        """
        Initialize Bedrock knowledge base.
        
        Args:
            region: AWS region for Bedrock service, defaults to config value if None
        """
        self.region = region or config.region
        self.client = boto3.client('bedrock-agent-runtime', region_name=self.region)
        self.knowledge_base_id = config.knowledge_base_id
        self.model_arn = config.model_arn
        self.prompt_template = config.prompt_template
    
    def _create_request(self, query: str, session_id: Optional[str] = None, 
                      use_decomposition: bool = True) -> Dict[str, Any]:
        """
        Create a request for the Bedrock knowledge base.
        
        Args:
            query: The user's query
            session_id: Optional session ID for maintaining conversation context
            use_decomposition: Whether to include query decomposition configuration
            
        Returns:
            A dictionary containing the request parameters
        """
        # Check if we're using an inference profile ARN
        is_inference_profile = "inference-profile" in self.model_arn
        
        # Prepare base request structure
        request = {
            'input': {'text': query},
            'retrieveAndGenerateConfiguration': {
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.knowledge_base_id,
                    'modelArn': self.model_arn,
                    'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': self.prompt_template
                        }
                    }
                }
            }
        }
        
        # Add query decomposition configuration for non-inference profiles when requested
        if not is_inference_profile and use_decomposition:
            request['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['orchestrationConfiguration'] = {
                'queryTransformationConfiguration': {
                    'type': 'QUERY_DECOMPOSITION'
                }
            }
        
        # Add session ID if available and not None
        if session_id is not None:
            request['sessionId'] = session_id
        
        return request
    
    def query(self, query: str, session_id: Optional[str] = None, 
              context_summary: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Query Bedrock knowledge base with session or context.
        
        Args:
            query: The user's query to the knowledge base
            session_id: Optional session ID for maintaining conversation context
            context_summary: Optional summary of previous conversation context
            
        Returns:
            A tuple containing (response_text, session_id)
            
        Note:
            This method attempts to query with session ID first, then falls back to 
            context summary if session is expired, and finally to plain query.
        """
        logger.info(f"Querying knowledge base with: {query[:100]}...")
        logger.info(f"Using model ARN: {self.model_arn}")
        
        # Check if we're using an inference profile
        is_inference_profile = "inference-profile" in self.model_arn
        
        # First attempt: Try with session_id if available
        if session_id:
            try:
                logger.info(f"Attempting query with session_id: {session_id}")
                if is_inference_profile:
                    return self._execute_query(query, session_id)
                else:
                    return self._query_with_fallback(query, session_id)
            except Exception as e:
                logger.warning(f"Session-based query failed (possibly expired session): {e}")
                # Session ID might be expired, fall through to context summary fallback
        
        # Second attempt: Use enhanced query with context summary (without session_id)
        if context_summary:
            logger.info("Falling back to context-enhanced query without session_id")
            enhanced_query = f"Previous conversation context:\n{context_summary}\n\nCurrent question: {query}"
            try:
                if is_inference_profile:
                    return self._execute_query(enhanced_query, None)
                else:
                    return self._query_with_fallback(enhanced_query, None)
            except Exception as e:
                logger.warning(f"Context-enhanced query failed: {e}")
                # Fall through to plain query
        
        # Third attempt: Just use the plain query as last resort
        logger.info("Using plain query without context or session")
        try:
            if is_inference_profile:
                return self._execute_query(query, None)
            else:
                return self._query_with_fallback(query, None)
        except Exception as e:
            logger.error(f"All query attempts failed: {e}", exc_info=True)
            return ("I'm sorry, I couldn't retrieve the information you requested. "
                   "There might be an issue with the knowledge base or the query format."), None
    
    def _execute_query(self, query: str, session_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Execute a single query against the knowledge base.
        
        Args:
            query: The user's query
            session_id: Optional session ID for maintaining conversation context
            
        Returns:
            A tuple containing (response_text, session_id)
            
        Raises:
            Exception: If the query execution fails, allowing caller to handle fallback logic
        """
        request = self._create_request(query, session_id)
        logger.info(f"Request: {json.dumps(request, indent=2)}")
        response = self.client.retrieve_and_generate(**request)
        return response['output']['text'], response.get('sessionId')
    
    def _query_with_fallback(self, query: str, session_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Try querying with decomposition first, then fall back to no decomposition.
        
        Args:
            query: The user's query
            session_id: Optional session ID for maintaining conversation context
            
        Returns:
            A tuple containing (response_text, session_id)
            
        Raises:
            Exception: If both query attempts fail, allowing caller to handle higher-level fallback logic
        """
        # Create request with query decomposition
        request = self._create_request(query, session_id)
        logger.info(f"Full request with decomposition: {json.dumps(request, indent=2)}")
        
        try:
            # Try with query decomposition first
            response = self.client.retrieve_and_generate(**request)
            logger.info("Query with decomposition succeeded")
            return response['output']['text'], response.get('sessionId')
        except Exception as e:
            logger.warning(f"Error with query decomposition: {e}")
            
            # If query decomposition fails, try without it
            logger.info("Retrying without query decomposition...")
            # Create a new request explicitly without query decomposition
            request_no_decomp = self._create_request(query, session_id, use_decomposition=False)
            
            logger.info(f"Fallback request: {json.dumps(request_no_decomp, indent=2)}")
            try:
                response = self.client.retrieve_and_generate(**request_no_decomp)
                logger.info("Query without decomposition succeeded")
                return response['output']['text'], response.get('sessionId')
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}", exc_info=True)
                # Re-raise the exception to allow the caller to handle higher-level fallbacks
                raise

def get_knowledge_base(kb_type: str = 'bedrock', region: Optional[str] = None) -> KnowledgeBaseInterface:
    """
    Get knowledge base implementation based on type.
    
    Args:
        kb_type: Type of knowledge base to create ('bedrock' is currently the only supported type)
        region: AWS region for Bedrock service, defaults to config value if None
        
    Returns:
        An implementation of KnowledgeBaseInterface
    """
    # Currently only supports Bedrock
    return BedrockKnowledgeBase(region)