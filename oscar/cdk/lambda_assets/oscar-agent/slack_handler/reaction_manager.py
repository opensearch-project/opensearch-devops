#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Reaction management for Slack Handler.
"""

import logging
from typing import List, Optional, Union
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class ReactionManager:
    """Manages Slack message reactions."""
    
    def __init__(self, client) -> None:
        """Initialize with Slack client.
        
        Args:
            client: Slack client instance
        """
        self.client = client
    
    def manage_reactions(self, channel: str, timestamp: str, add_reaction: Optional[str] = None, 
                        remove_reaction: Optional[Union[str, List[str]]] = None) -> None:
        """Add or remove reactions from a message.
        
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