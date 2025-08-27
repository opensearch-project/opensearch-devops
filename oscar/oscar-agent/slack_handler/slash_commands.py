#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Slash command handlers for Slack Handler.
"""

import logging
import time
from typing import Any, Callable, Dict

from config import config


logger = logging.getLogger(__name__)


class SlashCommandHandlers:
    """Handles Slack slash commands."""
    
    def __init__(self, message_processor, storage) -> None:
        """Initialize with message processor and storage.
        
        Args:
            message_processor: MessageProcessor instance
            storage: Storage instance
        """
        self.message_processor = message_processor
        self.storage = storage
    
    def handle_announce_command(self, ack, command, say) -> None:
        """Handle /announce slash command."""
        self._handle_slash_command(ack, command, say, "announce")
    
    def handle_assign_owner_command(self, ack, command, say) -> None:
        """Handle /assign-owner slash command."""
        self._handle_slash_command(ack, command, say, "assign_owner")
    
    def handle_request_owner_command(self, ack, command, say) -> None:
        """Handle /request-owner slash command."""
        self._handle_slash_command(ack, command, say, "request_owner")
    
    def handle_rc_details_command(self, ack, command, say) -> None:
        """Handle /rc-details slash command."""
        self._handle_slash_command(ack, command, say, "rc_details")
    
    def handle_missing_notes_command(self, ack, command, say) -> None:
        """Handle /missing-notes slash command."""
        self._handle_slash_command(ack, command, say, "missing_notes")
    
    def handle_integration_test_command(self, ack, command, say) -> None:
        """Handle /integration-test slash command."""
        self._handle_slash_command(ack, command, say, "integration_test")
    
    def handle_broadcast_command(self, ack, command, say) -> None:
        """Handle /broadcast slash command."""
        self._handle_broadcast_command(ack, command, say)
    
    def _handle_slash_command(self, ack, command, say, slash_command_type: str) -> None:
        """Handle slash commands by delegating to message processor."""
        ack()
        
        user_id = command.get('user_id')
        params = command.get('text', '').strip().split()
        
        # Require channel and version, RC is optional
        if len(params) < 2 or len(params) > 3:
            say(text=f"❌ Usage: `/{slash_command_type.replace('_', '-')} <channel_id_or_name> <version> [rc_number]`", response_type="ephemeral")
            return
        
        channel_param = params[0]
        version_param = params[1]
        rc_param = f" and RC{params[2]}" if len(params) == 3 else ""
        
        # Create synthetic parameters
        channel_id = command.get('channel_id')
        thread_ts = str(int(time.time()))
        
        # Generate query with RC parameter
        query_template = config.agent_queries.get(slash_command_type)
        if not query_template:
            say(text="❌ Unknown slash command type", response_type="ephemeral")
            return
        
        query = query_template.format(channel=channel_param, version=version_param, rc_param=rc_param)
        
        # Create a wrapper for say that captures the response and stores context efficiently
        def say_with_context_storage(text, **kwargs):
            response = say(text=text, **kwargs)
            if response and 'ts' in response:
                actual_thread_ts = response['ts']
                original_query = f"/{slash_command_type.replace('_', '-')} {channel_param} {version_param} {params[2] if len(params) == 3 else ''}".strip()
                self.storage.store_bot_message_context(channel_id, actual_thread_ts, text, None, original_query)
            return response
        
        # Process directly with context storage skipped (handled by say_with_context_storage)
        self.message_processor.process_message(channel_id, thread_ts, user_id, query, say_with_context_storage, thread_ts, skip_context_storage=True)
    
    def _handle_broadcast_command(self, ack, command, say) -> None:
        """Handle broadcast slash command for general queries."""
        ack()
        
        user_id = command.get('user_id')
        text = command.get('text', '').strip()
        
        # Parse channel and query
        parts = text.split(' ', 1)
        if len(parts) < 2:
            say(text="❌ Usage: `/oscar-broadcast <channel_id_or_name> <your_query>`", response_type="ephemeral")
            return
        
        channel_param = parts[0]
        user_query = parts[1]
        
        # Create synthetic parameters
        channel_id = command.get('channel_id')
        thread_ts = str(int(time.time()))
        
        # Generate query for processing
        query_template = config.agent_queries.get("broadcast")
        query = query_template.format(channel=channel_param, user_query=user_query)
        
        # Create a wrapper for say that captures the response and stores context efficiently
        def say_with_context_storage(text, **kwargs):
            response = say(text=text, **kwargs)
            if response and 'ts' in response:
                actual_thread_ts = response['ts']
                original_query = f"/oscar-broadcast {channel_param} {user_query}"
                self.storage.store_bot_message_context(channel_id, actual_thread_ts, text, None, original_query)
            return response
        
        # Process directly with context storage skipped (handled by say_with_context_storage)
        self.message_processor.process_message(channel_id, thread_ts, user_id, query, say_with_context_storage, thread_ts, skip_context_storage=True)