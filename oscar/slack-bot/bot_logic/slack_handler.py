"""
Slack handler module for OSCAR.

This module provides classes for handling Slack events and messages.
"""

import hashlib
import logging
from slack_bolt import App
from .config import config
from .storage import get_storage
from .bedrock import get_knowledge_base

# Configure logging
logger = logging.getLogger(__name__)

class SlackHandler:
    """Handler for Slack events and messages."""
    
    def __init__(self, app, storage=None, knowledge_base=None):
        """Initialize Slack handler."""
        self.app = app
        self.storage = storage or get_storage()
        self.knowledge_base = knowledge_base or get_knowledge_base()
    
    def create_event_id(self, event):
        """Create robust event fingerprint for unique message identification."""
        # Use exact timestamp for unique message ID
        message_ts = event['ts']
        content_hash = hashlib.md5(event['text'].encode()).hexdigest()[:8]
        
        return f"{event['channel']}_{event['user']}_{message_ts}_{content_hash}"
    
    def has_bot_responded(self, channel, message_ts):
        """Check if bot already responded to this specific message."""
        try:
            bot_user_id = self.app.client.auth_test()["user_id"]
            response = self.app.client.conversations_replies(
                channel=channel,
                ts=message_ts,
                limit=10
            )
            
            # Check if bot replied immediately after this specific message
            messages = response.get('messages', [])
            if len(messages) < 2:
                return False
                
            # Look for bot response right after the user message
            user_msg_ts = float(message_ts)
            for msg in messages[1:]:  # Skip original message
                if (msg.get('user') == bot_user_id and 
                    float(msg.get('ts', 0)) > user_msg_ts):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking if bot responded: {e}")
            return False
    
    def add_reaction(self, channel, timestamp, reaction):
        """Add a reaction to a message."""
        try:
            self.app.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=reaction
            )
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
    
    def remove_reaction(self, channel, timestamp, reaction):
        """Remove a reaction from a message."""
        try:
            self.app.client.reactions_remove(
                channel=channel,
                timestamp=timestamp,
                name=reaction
            )
        except Exception as e:
            logger.error(f"Error removing reaction: {e}")
    
    def update_reaction(self, channel, timestamp, old_reaction, new_reaction):
        """Update a reaction on a message."""
        self.remove_reaction(channel, timestamp, old_reaction)
        self.add_reaction(channel, timestamp, new_reaction)
    
    def handle_message(self, event, say, ack=None, is_dm=False):
        """Common message handling logic for both mentions and DMs."""
        # Acknowledge the event immediately if ack is provided
        if ack:
            ack()
        
        # Log the full event for debugging
        logger.info(f"Received event: {event}")
        
        # Multi-layer deduplication
        event_id = self.create_event_id(event)
        
        if self.storage.is_duplicate_event(event_id):
            logger.info(f"Duplicate event blocked: {event_id}")
            return
        
        # Check if bot already responded to this specific message
        if self.has_bot_responded(event["channel"], event["ts"]):
            logger.info(f"Already responded to message: {event['ts']}")
            return
        
        # Get thread_ts - this is the parent message timestamp or the current message timestamp if not in a thread
        thread_ts = event.get("thread_ts") or event["ts"]
        
        # Extract query
        if is_dm:
            query = event["text"].strip()
            # Log DM thread information for debugging
            logger.info(f"DM message received - thread_ts: {thread_ts}, original ts: {event['ts']}, channel: {event['channel']}")
            
            # For DMs in threads, ensure we're using the correct thread_ts
            if "thread_ts" in event:
                logger.info(f"This is a threaded DM reply - using thread_ts: {thread_ts}")
            else:
                logger.info(f"This is a new DM message - using message ts as thread_ts: {thread_ts}")
        else:
            # Remove bot mention for channel messages
            user_id = self.app.client.auth_test()["user_id"]
            query = event["text"].replace(f"<@{user_id}>", "").strip()
        
        # Add an emoji reaction to acknowledge the message
        self.add_reaction(event["channel"], event["ts"], "eyes")
        
        # Get thread context
        channel = event["channel"]
        session_id, context_summary = self.storage.get_session_context(thread_ts, channel)
        
        try:
            # Query knowledge base with context
            response_text, new_session_id = self.knowledge_base.query(query, session_id, context_summary)
            
            # Store context for future use
            self.storage.store_session_context(thread_ts, channel, new_session_id, query, response_text)
            
            # Reply in thread (both channels and DMs support threading)
            say(
                text=response_text,
                thread_ts=thread_ts
            )
            
            # Replace the "eyes" reaction with a "white_check_mark" to indicate completion
            self.update_reaction(event["channel"], event["ts"], "eyes", "white_check_mark")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
            # Replace the "eyes" reaction with an "x" to indicate an error
            self.update_reaction(event["channel"], event["ts"], "eyes", "x")
            
            say(
                text=f"❌ Sorry, I encountered an error: {str(e)}",
                thread_ts=thread_ts
            )
    
    def register_handlers(self):
        """Register event handlers with the Slack app."""
        @self.app.event("app_mention")
        def handle_mention(event, say, ack):
            """Handle direct mentions of the bot."""
            self.handle_message(event, say, ack, is_dm=False)
        
        # Only register DM handler if DM functionality is enabled
        if hasattr(config, 'enable_dm') and config.enable_dm:
            logger.info("DM functionality is enabled")
            @self.app.event("message")
            def handle_dm(event, say, ack):
                """Handle direct messages to the bot."""
                # Only handle DMs (not channel messages)
                if event.get("channel_type") == "im":
                    self.handle_message(event, say, ack, is_dm=True)
        else:
            logger.info("DM functionality is disabled")
        
        return self.app