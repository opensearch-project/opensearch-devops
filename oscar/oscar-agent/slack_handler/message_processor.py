#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Message processing for Slack Handler.
"""

import logging
import re
from config import config
import time
from typing import Any, Callable, Optional



logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes Slack messages and generates agent responses."""
    
    def __init__(self, storage, oscar_agent, reaction_manager, timeout_handler) -> None:
        """Initialize with required dependencies.
        
        Args:
            storage: Storage implementation for conversation context
            oscar_agent: OSCAR agent implementation for query processing
            reaction_manager: ReactionManager instance
            timeout_handler: TimeoutHandler instance
        """
        self.storage = storage
        self.oscar_agent = oscar_agent
        self.reaction_manager = reaction_manager
        self.timeout_handler = timeout_handler

    
    def extract_query(self, text: str) -> str:
        """Extract the query from the message text by removing mentions.
        
        Args:
            text: The raw message text
            
        Returns:
            The cleaned query text
        """
        # Remove mentions using configured pattern
        query = re.sub(config.patterns['mention'], '', text).strip()
        return query
    
    def add_user_context_to_query(self, query: str, user_id: str) -> str:
        """Add user context to query for sensitive operations."""
        return f"[USER_ID: {user_id}] {query}"
    
    def _handle_confirmation_detection(self, response: str, channel: str, thread_ts: str) -> str:
        """Handle confirmation detection and warning reaction management.
        
        Args:
            response: The agent's response text
            channel: Slack channel ID
            thread_ts: Thread timestamp (original user message)
            
        Returns:
            Cleaned response with confirmation marker removed
        """
        if response and '[CONFIRMATION_REQUIRED]' in response:
            # Remove the marker from the response
            cleaned_response = response.replace('[CONFIRMATION_REQUIRED]', '').strip()
            
            # Add warning reaction to the original user message
            self.reaction_manager.manage_reactions(
                channel, 
                thread_ts,  # This is the original user message timestamp
                add_reaction="warning"
            )
            logger.info(f"Added warning reaction to original message {thread_ts} due to confirmation requirement")
            
            return cleaned_response
        
        return response

    def is_fully_authorized_user(self, user_id: str) -> bool:
        """
        Check if a user is fully authorized to use privileged features.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if the user is fully authorized, False otherwise
        """
        is_authorized = user_id in config.fully_authorized_users
        logger.debug(f"User {user_id} authorization check: {is_authorized}")
        return is_authorized
    
    def process_message(self, channel: str, thread_ts: str, user_id: str, 
                       text: str, say: Callable, message_ts: str = None, 
                       slash_command: str = None, skip_context_storage: bool = False) -> None:
        """Process a message and generate a response using the OSCAR agent.
        
        Args:
            channel: Slack channel ID
            thread_ts: Thread timestamp for threading replies
            user_id: User ID of the message sender
            text: Message text (for slash commands, this is the channel parameter)
            say: Function to send a message to the channel
            message_ts: Timestamp of the specific message to react to (may differ from thread_ts)
            slash_command: Type of slash command if this is a slash command invocation
            skip_context_storage: Whether to skip context storage (for slash commands)
        """
        # Use message_ts if provided, otherwise fall back to thread_ts
        # This ensures we react to the specific message, not just the thread parent
        reaction_ts = message_ts if message_ts else thread_ts
        
        # Generate thread key for context storage
        thread_key = f"{channel}_{thread_ts}"
        
        logger.info(f"Processing message in channel {channel}, thread {thread_ts}, from user {user_id}")
        
        self.reaction_manager.manage_reactions(channel, reaction_ts, add_reaction="thinking_face")
        
        start_time = time.time()
        
        try:
            # Extract or generate query based on source
            if slash_command or 'im' in channel:
                # For slash commands, text is already the formatted query
                query = text
                logger.info(f"Using pre-formatted slash command query: {query}")
            else:
                # For regular messages, extract query from text (remove mentions)
                query = self.extract_query(text)
                logger.info(f"Extracted query: {query}")
            
            # ALWAYS add user context to query for agent to use as needed
            query = self.add_user_context_to_query(query, user_id)
            logger.info(f"Added user context to query: {query}")
            logger.info(f"Processing automated message sending request from authorized user {user_id}")
                # Continue with normal agent processing - agent will handle message sending via action group
            
            # Get context from storage and format for query
            stored_context = self.storage.get_context(thread_key)
            session_id = stored_context.get("session_id") if stored_context else None
            
            # Get formatted context for the query
            formatted_context = self.storage.get_context_for_query(thread_key)
            
            # Query OSCAR agent with timeout monitoring (using formatted context)
            privilege = self.is_fully_authorized_user(user_id)
            response, new_session_id = self.timeout_handler.query_agent_with_timeout(
                self.oscar_agent, query, privilege, session_id, formatted_context, channel, reaction_ts, 
                start_time, say, thread_ts, user_id
            )
            
            # If timeout occurred, response will be None
            if response is None:
                return
            
            # Handle confirmation detection and warning reaction
            response = self._handle_confirmation_detection(response, channel, thread_ts)
            
            # Validate response - handle None, empty, or whitespace-only responses
            if response is None:
                logger.warning(f"OSCAR agent returned None response for query: {query}")
                response = "I'm having trouble generating a response right now. Please try again."
            elif not response or response.strip() == "":
                logger.warning(f"OSCAR agent returned empty response for query: {query}")
                response = "I'm having trouble generating a response right now. Please try again."
            else:
                # Ensure response is a string
                response = str(response).strip()
            
            # Update context with new query and response (skip for slash commands to avoid duplication)
            if not skip_context_storage:
                self.storage.update_context(thread_key, query, response, session_id, new_session_id)
            
            # Format response for Slack before sending
            from .message_formatter import MessageFormatter
            formatter = MessageFormatter()
            formatted_response = formatter.format_markdown_to_slack_mrkdwn(response)
            formatted_response = formatter.convert_at_symbols_to_slack_pings(formatted_response)
            

            
            # Send response
            say(text=formatted_response, thread_ts=thread_ts)
            logger.info(f"Successfully sent response to thread {thread_ts}")
            
            # Log performance
            end_time = time.time()
            total_elapsed = end_time - start_time
            logger.info(f"Query processed in {total_elapsed:.2f} seconds")
            
            # Add success reaction and remove processing reactions
            self.reaction_manager.manage_reactions(
                channel, 
                reaction_ts, 
                add_reaction="white_check_mark", 
                remove_reaction=["thinking_face", "hourglass_flowing_sand"]
            )
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Update reactions: remove processing reactions, add x
            self.reaction_manager.manage_reactions(
                channel, 
                reaction_ts, 
                add_reaction="x", 
                remove_reaction=["thinking_face", "hourglass_flowing_sand"]
            )
            
            # Send user-friendly error message based on error type
            try:
                error_str = str(e).lower()
                if 'throttl' in error_str or 'rate' in error_str or 'throttle' in error_str:
                    error_message = "I'm currently experiencing high load. Please wait a moment and try again."
                elif 'timeout' in error_str:
                    error_message = "Your request is taking longer than expected. Please try a simpler question."
                elif 'nonetype' in error_str:
                    error_message = "I'm having trouble generating a response. Please try rephrasing your question."
                else:
                    error_message = "Sorry, I encountered an error while processing your request. Please try again later."
                
                # Ensure error_message is not None
                if error_message is None or error_message.strip() == "":
                    error_message = "An unexpected error occurred. Please try again."
                    
                # Format error message for Slack before sending
                from .message_formatter import MessageFormatter
                formatter = MessageFormatter()
                formatted_error = formatter.format_markdown_to_slack_mrkdwn(error_message)
                formatted_error = formatter.convert_at_symbols_to_slack_pings(formatted_error)
                
                say(text=formatted_error, thread_ts=thread_ts)
            except Exception as say_error:
                logger.error(f"Error sending error message: {say_error}", exc_info=True)
                # Last resort - try to send a basic message
                try:
                    say(text="Error occurred. Please try again.", thread_ts=thread_ts)
                except:
                    logger.error("Failed to send any error message to Slack")