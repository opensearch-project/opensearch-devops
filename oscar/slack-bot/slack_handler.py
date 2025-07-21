#!/usr/bin/env python
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Slack event handler module for OSCAR.

This module provides the SlackHandler class for handling Slack events.
"""

import logging
import time
import re
from typing import Dict, Any, Optional, Callable, List, Tuple, Union

from slack_bolt import App
from slack_sdk.errors import SlackApiError

from config import config
from storage import StorageInterface
from bedrock import KnowledgeBaseInterface

# Configure logging
logger = logging.getLogger(__name__)

class SlackHandler:
    """Handler for Slack events."""
    
    def __init__(self, app: App, storage: StorageInterface, knowledge_base: KnowledgeBaseInterface) -> None:
        """
        Initialize Slack handler with app, storage, and knowledge base.
        
        Args:
            app: Slack Bolt app instance
            storage: Storage implementation for persisting conversation context
            knowledge_base: Knowledge base implementation for answering queries
        """
        self.app = app
        self.storage = storage
        self.knowledge_base = knowledge_base
        self.client = app.client
    
    def register_handlers(self) -> App:
        """
        Register event handlers with the Slack app.
        
        Returns:
            The Slack Bolt app instance with handlers registered
        """
        # Register app_mention handler
        self.app.event("app_mention")(self.handle_app_mention)
        
        # Register message handler for DMs if enabled
        # Use the imported config module for consistency with tests
        from config import config as config_instance
        if config_instance.enable_dm:
            self.app.message()(self.handle_message)
        
        logger.info("Registered Slack event handlers")
        return self.app
    
    def handle_app_mention(self, event: Dict[str, Any], say: Callable) -> None:
        """
        Handle app_mention events.
        
        Args:
            event: Slack event data
            say: Function to send a message to the channel
        """
        # Extract message details
        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")
        user_id = event.get("user")
        text = event.get("text")
        event_ts = event.get("ts")  # Use ts for the specific message, not thread_ts
        
        logger.info(f"Processing app_mention event: channel={channel}, ts={event_ts}, thread_ts={thread_ts}")
        
        # Process the message
        self._process_message(channel, thread_ts, user_id, text, say, message_ts=event_ts)
    
    def handle_message(self, message: Dict[str, Any], say: Callable) -> None:
        """
        Handle direct message events.
        
        Args:
            message: Slack message data
            say: Function to send a message to the channel
        """
        # Only process DM messages
        channel_type = message.get("channel_type")
        if channel_type != "im":
            return
        
        # Extract message details
        channel = message.get("channel")
        thread_ts = message.get("thread_ts") or message.get("ts")
        user_id = message.get("user")
        text = message.get("text")
        event_ts = message.get("ts")  # Use ts for the specific message
        
        logger.info(f"Processing DM message event: channel={channel}, ts={event_ts}, thread_ts={thread_ts}")
        
        # Process the message
        self._process_message(channel, thread_ts, user_id, text, say, message_ts=event_ts)
    
    # Keep _is_duplicate_event for test compatibility
    def _is_duplicate_event(self, event: Dict[str, Any]) -> bool:
        """
        Check if this is a duplicate event using event timestamp.
        
        Args:
            event: Slack event data
            
        Returns:
            True if the event is a duplicate, False otherwise
        """
        # Get primary event identifier
        event_id = event.get("event_ts") or event.get("ts")
        if not event_id:
            logger.warning("Event has no timestamp identifier, cannot deduplicate")
            return False
        
        # Check if we've seen this event before
        if self.storage.has_seen_event(event_id):
            logger.info(f"Detected duplicate event: {event_id}")
            return True
        
        # Mark event as seen
        self.storage.mark_event_seen(event_id)
        logger.info(f"New event marked as seen: {event_id}")
        return False
    
    def _extract_query(self, text: str) -> str:
        """
        Extract the query from the message text by removing mentions.
        
        Args:
            text: The raw message text
            
        Returns:
            The cleaned query text
        """
        # Remove mentions (e.g., <@U12345>)
        query = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
        return query
    
    def _update_context(self, thread_key: str, query: str, response: str, 
                       session_id: Optional[str], new_session_id: Optional[str]) -> Dict[str, Any]:
        """
        Update the conversation context with the new query and response.
        
        Args:
            thread_key: The unique key for the thread
            query: The user's query
            response: The bot's response
            session_id: The current session ID
            new_session_id: The new session ID from the knowledge base
            
        Returns:
            The updated context
        """
        # Get existing context or create a new one
        context = self.storage.get_context(thread_key)
        if not context:
            context = {
                "session_id": new_session_id,
                "history": [],
                "summary": ""
            }
        
        # Update session ID if it changed
        if new_session_id and new_session_id != session_id:
            context["session_id"] = new_session_id
        
        # Append to history
        context["history"].append({
            "query": query,
            "response": response,
            "timestamp": int(time.time())
        })
        
        # Generate summary (simple for now, just the last few exchanges)
        history_text = ""
        for entry in context["history"][-3:]:  # Last 3 exchanges
            history_text += f"User: {entry['query']}\nAssistant: {entry['response']}\n\n"
        context["summary"] = history_text[:config.context_summary_length]
        
        # Store updated context
        self.storage.store_context(thread_key, context)
        
        return context
    
    def _manage_reactions(self, channel: str, timestamp: str, add_reaction: Optional[str] = None, 
                         remove_reaction: Optional[Union[str, List[str]]] = None) -> None:
        """
        Add or remove reactions from a message.
        
        Args:
            channel: The Slack channel ID
            timestamp: The message timestamp
            add_reaction: The reaction to add (optional)
            remove_reaction: The reaction(s) to remove (optional, can be a string or list of strings)
        """
        try:
            # Remove reaction(s) if specified
            if remove_reaction:
                # Handle both single reaction and list of reactions
                reactions_to_remove = [remove_reaction] if isinstance(remove_reaction, str) else remove_reaction
                
                for reaction in reactions_to_remove:
                    try:
                        self.client.reactions_remove(
                            channel=channel,
                            timestamp=timestamp,
                            name=reaction
                        )
                        logger.info(f"Removed {reaction} reaction from message {timestamp}")
                    except SlackApiError as e:
                        # Ignore errors for reactions that don't exist
                        if "no_reaction" in str(e):
                            logger.debug(f"Reaction {reaction} not found on message {timestamp}")
                        else:
                            logger.warning(f"Error removing reaction {reaction}: {e}")
            
            # Add reaction if specified
            if add_reaction:
                try:
                    self.client.reactions_add(
                        channel=channel,
                        timestamp=timestamp,
                        name=add_reaction
                    )
                    logger.info(f"Added {add_reaction} reaction to message {timestamp}")
                except SlackApiError as e:
                    # Ignore errors for reactions that already exist
                    if "already_reacted" in str(e):
                        logger.debug(f"Reaction {add_reaction} already exists on message {timestamp}")
                    else:
                        logger.warning(f"Error adding reaction {add_reaction}: {e}")
        except Exception as e:
            logger.warning(f"Error managing reactions: {e}")
    
    def _process_message(self, channel: str, thread_ts: str, user_id: str, 
                        text: str, say: Callable, message_ts: str = None) -> None:
        """
        Process a message and generate a response.
        
        Args:
            channel: Slack channel ID
            thread_ts: Thread timestamp for threading replies
            user_id: User ID of the message sender
            text: Message text
            say: Function to send a message to the channel
            message_ts: Timestamp of the specific message to react to (may differ from thread_ts)
        """
        # Use message_ts if provided, otherwise fall back to thread_ts
        # This ensures we react to the specific message, not just the thread parent
        reaction_ts = message_ts if message_ts else thread_ts
        
        # Generate thread key for context storage
        thread_key = f"{channel}_{thread_ts}"
        
        logger.info(f"Processing message in channel {channel}, thread {thread_ts}, from user {user_id}")
        
        # Add thinking reaction to the specific message
        self._manage_reactions(channel, reaction_ts, add_reaction="thinking_face")
        
        # Set timeout threshold (60 seconds)
        timeout_threshold = 60
        start_time = time.time()
        
        try:
            # Extract query from text (remove mentions)
            query = self._extract_query(text)
            logger.info(f"Extracted query: {query}")
            
            # Get context from storage
            context = self.storage.get_context(thread_key)
            context_summary = context.get("summary") if context else None
            session_id = context.get("session_id") if context else None
            
            # Check if we're approaching timeout before querying knowledge base
            current_time = time.time()
            if current_time - start_time > timeout_threshold * 0.3:  # 30% of timeout threshold
                # Add timer emoji to indicate potential slow response
                self._manage_reactions(channel, reaction_ts, add_reaction="timer_clock")
            
            # Query knowledge base
            kb_start_time = time.time()
            response, new_session_id = self.knowledge_base.query(
                query, 
                session_id=session_id,
                context_summary=context_summary
            )
            kb_end_time = time.time()
            logger.info(f"Knowledge base query completed in {kb_end_time - kb_start_time:.2f} seconds")
            
            # Update context with new query and response
            self._update_context(thread_key, query, response, session_id, new_session_id)
            
            # Send response
            say(text=response, thread_ts=thread_ts)
            logger.info(f"Successfully sent response to thread {thread_ts}")
            
            # Log performance
            end_time = time.time()
            total_elapsed = end_time - start_time
            logger.info(f"Query processed in {total_elapsed:.2f} seconds")
            
            # Update reactions based on processing time
            reactions_to_remove = ["thinking_face"]
            if total_elapsed > timeout_threshold:
                # Keep timer_clock reaction if it was a slow response
                logger.info(f"Response took longer than timeout threshold: {total_elapsed:.2f}s > {timeout_threshold}s")
            else:
                # Remove timer_clock if it was added
                reactions_to_remove.append("timer_clock")
                
            # Add success reaction and remove processing reactions
            self._manage_reactions(
                channel, 
                reaction_ts, 
                add_reaction="white_check_mark", 
                remove_reaction=reactions_to_remove
            )
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Update reactions: remove thinking_face and timer_clock if present, add x
            self._manage_reactions(
                channel, 
                reaction_ts, 
                add_reaction="x", 
                remove_reaction=["thinking_face", "timer_clock"]
            )
            
            # Send user-friendly error message
            try:
                error_message = "Sorry, I encountered an error while processing your request. Please try again later."
                say(text=error_message, thread_ts=thread_ts)
            except Exception as say_error:
                logger.error(f"Error sending error message: {say_error}", exc_info=True)