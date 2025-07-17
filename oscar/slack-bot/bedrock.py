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
    
    def _create_request(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a request for the Bedrock knowledge base.
        
        Args:
            query: The user's query
            session_id: Optional session ID for maintaining conversation context
            
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
        
        # Add query decomposition configuration for non-inference profiles
        if not is_inference_profile:
            request['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['orchestrationConfiguration'] = {
                'queryTransformationConfiguration': {
                    'type': 'QUERY_DECOMPOSITION'
                }
            }
        
        # Add session ID if available
        if session_id:
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
            
        Raises:
            Exception: If both the primary query and fallback query fail
        """
        # Build prompt with context if available
        if context_summary and not session_id:
            enhanced_query = f"Previous conversation context:\n{context_summary}\n\nCurrent question: {query}"
        else:
            enhanced_query = query
        
        logger.info(f"Querying knowledge base with: {enhanced_query[:100]}...")
        logger.info(f"Using model ARN: {self.model_arn}")
        
        # Create request
        request = self._create_request(enhanced_query, session_id)
        
        # Log the full request for debugging
        logger.info(f"Full request: {json.dumps(request, indent=2)}")
        
        try:
            # Try with query decomposition first
            response = self.client.retrieve_and_generate(**request)
            logger.info("Query with decomposition succeeded")
            return response['output']['text'], response.get('sessionId')
        except Exception as e:
            logger.warning(f"Error with query decomposition: {e}")
            
            # If query decomposition fails, try without it
            logger.info("Retrying without query decomposition...")
            try:
                # Create a new request without query decomposition
                request_no_decomp = self._create_request(enhanced_query, session_id)
                
                # Remove orchestration configuration if it exists
                if 'orchestrationConfiguration' in request_no_decomp['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']:
                    del request_no_decomp['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['orchestrationConfiguration']
                
                logger.info(f"Fallback request: {json.dumps(request_no_decomp, indent=2)}")
                response = self.client.retrieve_and_generate(**request_no_decomp)
                logger.info("Query without decomposition succeeded")
                return response['output']['text'], response.get('sessionId')
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}", exc_info=True)
                # Return user-friendly error message instead of raising the exception
                return "I'm sorry, I couldn't retrieve the information you requested. There might be an issue with the knowledge base or the query format.", None

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