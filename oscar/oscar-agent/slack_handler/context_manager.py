#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Context management for Slack Handler.
"""

import logging
import time
from config import config
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages conversation context for Slack threads."""
    
    def __init__(self, storage) -> None:
        """Initialize with storage interface.
        
        Args:
            storage: Storage implementation for conversation context
        """
        self.storage = storage
    
    def update_context(self, thread_key: str, query: str, response: str, 
                      session_id: Optional[str], new_session_id: Optional[str]) -> Dict[str, Any]:
        """Update the conversation context with the new query and response.
        
        Args:
            thread_key: The unique key for the thread
            query: The user's query
            response: The agent's response
            session_id: The current session ID
            new_session_id: The new session ID from the agent
            
        Returns:
            The updated context
        """
        try:
            logger.info(f"🔄 UPDATE_CONTEXT: Starting update for thread_key='{thread_key}'")
            logger.info(f"🔄 UPDATE_CONTEXT: query_len={len(query)}, response_len={len(response)}, session_id='{session_id}', new_session_id='{new_session_id}'")
            
            # Get existing context or create a new one
            context = self.storage.get_context(thread_key)
            if not context:
                logger.info(f"🆕 UPDATE_CONTEXT: Creating new context for thread {thread_key}")
                context = {
                    "session_id": new_session_id or session_id,
                    "history": []
                }
            else:
                current_history_count = len(context.get('history', []))
                current_session = context.get('session_id')
                logger.info(f"🔄 UPDATE_CONTEXT: Updating existing context for thread {thread_key} (current history: {current_history_count} entries, current session: '{current_session}')")
            
            # Update session ID - prefer new_session_id, but keep existing if new one is None
            old_session_id = context.get("session_id")
            if new_session_id:
                if new_session_id != old_session_id:
                    logger.info(f"🔄 UPDATE_CONTEXT: Session ID changed from '{old_session_id}' to '{new_session_id}'")
                context["session_id"] = new_session_id
            elif session_id and not context.get("session_id"):
                # If we have a session_id but context doesn't, use it
                logger.info(f"🔄 UPDATE_CONTEXT: Setting session ID to '{session_id}' (was None)")
                context["session_id"] = session_id
            else:
                logger.info(f"🔄 UPDATE_CONTEXT: Keeping existing session ID '{old_session_id}'")
            
            # Ensure history exists
            if "history" not in context:
                context["history"] = []
                logger.info(f"🔧 UPDATE_CONTEXT: Added empty history array")
            
            # Append to history (no size limits - let the agent handle context)
            new_entry = {
                "query": query,
                "response": response,
                "timestamp": int(time.time())
            }
            context["history"].append(new_entry)
            new_history_count = len(context['history'])
            logger.info(f"✅ UPDATE_CONTEXT: Added new entry to history. Total entries: {new_history_count}")
            logger.info(f"📝 UPDATE_CONTEXT: New entry - query_preview='{query[:config.query_preview_length]}...', response_preview='{response[:config.response_preview_length]}...', timestamp={new_entry['timestamp']}")
            
            # Store updated context
            logger.info(f"💾 UPDATE_CONTEXT: About to store updated context for thread {thread_key}")
            success = self.storage.store_context(thread_key, context)
            if success:
                logger.info(f"✅ UPDATE_CONTEXT: Successfully stored context for thread {thread_key}")
            else:
                logger.error(f"❌ UPDATE_CONTEXT: Failed to store context for thread {thread_key}")
            
            return context
            
        except Exception as e:
            logger.error(f"❌ UPDATE_CONTEXT: Error updating context for thread {thread_key}: {e}", exc_info=True)
            # Return a minimal context to prevent complete failure
            minimal_context = {
                "session_id": new_session_id or session_id,
                "history": [{"query": query, "response": response, "timestamp": int(time.time())}]
            }
            logger.info(f"🔧 UPDATE_CONTEXT: Returning minimal context as fallback")
            return minimal_context
    
    def store_bot_message_context(self, channel: str, thread_ts: str, bot_message: str, 
                                 session_id: Optional[str] = None, user_query: str = None) -> None:
        """Store context for bot-initiated messages to enable follow-up conversations.
        
        Args:
            channel: Slack channel ID
            thread_ts: Thread timestamp for the message
            bot_message: The message sent by the bot
            session_id: Session ID if available
            user_query: Original user query that triggered this bot message (for slash commands)
        """
        thread_key = f"{channel}_{thread_ts}"
        
        # Create context for bot-initiated message
        context = {
            "session_id": session_id,
            "history": []
        }
        
        # If there was a user query (slash command), add it to history
        if user_query:
            context["history"].append({
                "query": user_query,
                "response": bot_message,
                "timestamp": int(time.time())
            })
        else:
            # For pure bot-initiated messages, create a synthetic entry
            context["history"].append({
                "query": "[Bot initiated conversation]",
                "response": bot_message,
                "timestamp": int(time.time())
            })
        
        # Store the context
        self.storage.store_context(thread_key, context)
        logger.info(f"Stored bot message context for thread {thread_ts}")