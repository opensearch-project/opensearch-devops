#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

"""
Main Slack Handler for OSCAR Agent.

This module provides comprehensive Slack event handling with agent integration,
including message processing, reaction management, and context preservation.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict
from slack_bolt import App

from config import config
from bedrock import OSCARAgentInterface
from context_storage import StorageInterface

from config import config
from slack_handler.reaction_manager import ReactionManager

from slack_handler.timeout_handler import TimeoutHandler
from slack_handler.message_processor import MessageProcessor
from slack_handler.event_handlers import EventHandlers
from slack_handler.slash_commands import SlashCommandHandlers
from slack_handler.slack_messaging import SlackMessaging

logger = logging.getLogger(__name__)


class SlackHandler:
    """Comprehensive Slack event handler with OSCAR agent integration.
    
    This class manages all Slack interactions including:
    - Event registration and processing
    - Message parsing and query extraction
    - Agent invocation and response handling
    - Reaction management for user feedback
    - Context preservation across conversations
    """
    
    def __init__(
        self, 
        app: App, 
        storage: StorageInterface, 
        oscar_agent: OSCARAgentInterface
    ) -> None:
        """Initialize Slack handler with required dependencies.
        
        Args:
            app: Slack Bolt app instance
            storage: Storage implementation for conversation context
            oscar_agent: OSCAR agent implementation for query processing
        """
        self.app = app
        self.storage = storage
        self.oscar_agent = oscar_agent
        self.client = app.client
        
        # Thread pool for better scaling
        self.executor = ThreadPoolExecutor(
            max_workers=config.max_workers, 
            thread_name_prefix=config.slack_handler_thread_prefix
        )
        
        # Initialize components
        self.reaction_manager = ReactionManager(self.client)
        self.timeout_handler = TimeoutHandler(self.reaction_manager)
        self.message_processor = MessageProcessor(
            self.storage, 
            self.oscar_agent, 
            self.reaction_manager, 
            self.timeout_handler
        )
        self.event_handlers = EventHandlers(self.message_processor)
        self.slash_commands = SlashCommandHandlers(self.message_processor, self.storage)
        self.slack_messaging = SlackMessaging(self.client, self.storage)
    
    def register_handlers(self) -> App:
        """Register event handlers with the Slack app.
        
        Returns:
            The Slack Bolt app instance with handlers registered
        """
        # Register app_mention handler
        self.app.event("app_mention")(self.event_handlers.handle_app_mention)
        
        # Register message handler for DMs if enabled
        if config.enable_dm:
            self.app.message()(self.event_handlers.handle_message)
        
        # Register slash command handlers for message orchestration
        self.app.command("/oscar-announce")(self.slash_commands.handle_announce_command)
        self.app.command("/oscar-assign-owner")(self.slash_commands.handle_assign_owner_command)
        self.app.command("/oscar-request-owner")(self.slash_commands.handle_request_owner_command)
        self.app.command("/oscar-rc-details")(self.slash_commands.handle_rc_details_command)
        self.app.command("/oscar-missing-notes")(self.slash_commands.handle_missing_notes_command)
        self.app.command("/oscar-integration-test")(self.slash_commands.handle_integration_test_command)
        self.app.command("/oscar-broadcast")(self.slash_commands.handle_broadcast_command)
        
        logger.info("Registered Slack event handlers and slash commands for OSCAR agent")
        return self.app
    
    def send_slack_message(self, channel: str, message: str) -> Dict[str, Any]:
        """Send a message to a Slack channel.
        
        This method is called by the supervisor agent's action group function.
        
        Args:
            channel: Target Slack channel ID or name
            message: Message content to send
            
        Returns:
            Dictionary with send result
        """
        return self.slack_messaging.send_slack_message(channel, message)