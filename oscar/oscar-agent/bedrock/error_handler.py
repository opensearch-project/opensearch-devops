#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Error Handler Module for OSCAR Agent.

This module provides error handling utilities for the OSCAR agent,
including session expiration detection and user-friendly error messages.
"""

import logging
from typing import Any

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AgentErrorHandler:
    """Handles error processing and user-friendly message generation for OSCAR agent."""
    
    @staticmethod
    def is_session_expired_error(error: Exception) -> bool:
        """
        Check if the error indicates a session expiration.
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error indicates session expiration
        """
        if isinstance(error, ClientError):
            error_code = error.response['Error']['Code']
            error_message = error.response['Error']['Message'].lower()
            
            # Check for session-related errors using match-case
            match error_code:
                case 'ValidationException' | 'BadRequestException':
                    session_keywords = ['session', 'expired', 'invalid']
                    if any(keyword in error_message for keyword in session_keywords):
                        return True
                case _:
                    pass
        
        # Check error message for session-related keywords
        error_str = str(error).lower()
        session_keywords = ['session expired', 'invalid session', 'session not found', 'session timeout']
        return any(keyword in error_str for keyword in session_keywords)
    
    @staticmethod
    def handle_agent_error(error: Exception, query: str) -> str:
        """
        Convert agent errors to user-friendly messages.
        
        Args:
            error: The exception that occurred
            query: The original query that failed
            
        Returns:
            A user-friendly error message
        """
        if isinstance(error, ClientError):
            error_code = error.response['Error']['Code']
            
            match error_code:
                case 'AccessDeniedException':
                    return "I don't have permission to access that information. Please contact your administrator."
                case 'ThrottlingException' | 'throttlingException':
                    return "I'm currently experiencing high load. Please wait a moment and try again."
                case 'ValidationException':
                    return "There was an issue with your query format. Please try rephrasing your question."
                case 'ResourceNotFoundException':
                    return "The agent or knowledge base is not available. Please contact your administrator."
                case 'ServiceUnavailableException' | 'InternalServerException':
                    return "The service is temporarily unavailable. Please try again in a few minutes."
                case _:
                    # Fall through to general error handling
                    pass
        
        # Handle other error types
        match error:
            case TimeoutError():
                return "Your query is taking longer than expected. Please try a more specific question or try again later."
            case _ if 'throttl' in str(error).lower():
                return "I'm currently experiencing high load. Please wait a moment and try again."
            case _:
                # Default case for unexpected errors
                logger.error("Unexpected agent error: %s", error, exc_info=True)
                return "I encountered an unexpected error. Please try again or contact support if this continues."