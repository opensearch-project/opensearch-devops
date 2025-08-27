#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Timeout handling for agent queries.
"""

import logging
import time
import threading
import queue
from typing import Any, Callable, Optional, Tuple

from config import config

logger = logging.getLogger(__name__)


class TimeoutHandler:
    """Handles agent query timeouts and monitoring."""
    
    def __init__(self, reaction_manager):
        """Initialize with reaction manager.
        
        Args:
            reaction_manager: ReactionManager instance for managing reactions
        """
        self.reaction_manager = reaction_manager
        self.active_queries = {}
        self.monitor_lock = threading.Lock()
    
    def query_agent_with_timeout(self, oscar_agent, query: str, privilege: bool, session_id: str, context_summary: str, 
                                channel: str, reaction_ts: str, start_time: float,
                                say: Callable, thread_ts: str, user_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Query the agent with timeout monitoring using simple threading with limits.
        
        Args:
            oscar_agent: OSCAR agent instance
            query: User query
            session_id: Session ID
            context_summary: Context summary
            channel: Slack channel ID
            reaction_ts: Timestamp for reactions
            start_time: Query start time
            say: Function to send messages
            thread_ts: Thread timestamp
            user_id: User ID
            
        Returns:
            Tuple of (response, new_session_id) or (None, None) if timeout/error
        """
        # Simple system overload protection
        query_id = f"{channel}_{thread_ts}_{int(start_time)}"
        
        with self.monitor_lock:
            if len(self.active_queries) >= config.max_active_queries:
                self.reaction_manager.manage_reactions(channel, reaction_ts, add_reaction="x", remove_reaction="thinking_face")
                say(text="🚫 System is currently overloaded. Please try again in a few minutes.", thread_ts=thread_ts)
                return None, None
            
            # Register query for timeout tracking only
            self.active_queries[query_id] = {
                'start_time': start_time,
                'user_id': user_id,
                'cancelled': False
            }
        
        result_queue = queue.Queue()
        hourglass_added = False
        
        def agent_worker():
            try:
                # Check if cancelled before starting
                with self.monitor_lock:
                    if self.active_queries.get(query_id, {}).get('cancelled'):
                        result_queue.put(("cancelled", "Query was cancelled", None))
                        self.active_queries.pop(query_id, None)
                        return
                
                # Query the agent
                response, new_session_id = oscar_agent.query(
                    query, privilege, session_id=session_id, context_summary=context_summary
                )
                result_queue.put(("success", response, new_session_id))
            except Exception as e:
                result_queue.put(("error", str(e), None))
        
        # Start agent in background thread
        thread = threading.Thread(target=agent_worker, daemon=True)
        thread.start()
        
        # Monitor every configured interval for better timing accuracy
        while thread.is_alive():
            try:
                # Wait for configured interval for result
                status, response, new_session_id = result_queue.get(timeout=config.monitor_interval)
                
                # Clean up on success
                with self.monitor_lock:
                    self.active_queries.pop(query_id, None)
                
                if status == "success":
                    return response, new_session_id
                elif status == "cancelled":
                    logger.warning(f"Query {query_id} was cancelled")
                    return None, None
                else:
                    raise Exception(response)
                    
            except queue.Empty:
                # Check elapsed time
                elapsed = time.time() - start_time
                logger.info(f"TIMEOUT CHECK: Query {query_id} still running after {elapsed:.2f}s (hourglass_added={hourglass_added})")
                
                # Add hourglass at threshold
                if elapsed >= config.hourglass_threshold and not hourglass_added:
                    logger.warning(f"ADDING HOURGLASS: After {elapsed:.2f}s for query {query_id}")
                    try:
                        self.reaction_manager.manage_reactions(channel, reaction_ts, add_reaction="hourglass_flowing_sand")
                        hourglass_added = True
                        logger.warning(f"HOURGLASS ADDED SUCCESSFULLY for {query_id}")
                    except Exception as e:
                        logger.error(f"FAILED TO ADD HOURGLASS: {e}")
                
                # Timeout at threshold
                if elapsed >= config.timeout_threshold:
                    logger.error(f"TIMEOUT TRIGGERED: Query {query_id} timed out after {elapsed:.2f}s")
                    
                    # Force thread termination attempt (though this won't stop Bedrock)
                    logger.warning(f"Thread still alive: {thread.is_alive()}, attempting cleanup")
                    
                    # Mark as cancelled
                    with self.monitor_lock:
                        query_info = self.active_queries.get(query_id)
                        if query_info:
                            query_info['cancelled'] = True
                        self.active_queries.pop(query_id, None)
                    
                    try:
                        self.reaction_manager.manage_reactions(channel, reaction_ts, add_reaction="x", 
                                                            remove_reaction=["thinking_face", "hourglass_flowing_sand"])
                        say(text="⏱️ Your request took too long and timed out. Please try a simpler question.", 
                            thread_ts=thread_ts)
                        logger.warning(f"TIMEOUT HANDLED SUCCESSFULLY for {query_id}")
                    except Exception as e:
                        logger.error(f"FAILED TO HANDLE TIMEOUT: {e}")
                    
                    # Break out of monitoring loop and return None
                    return None, None
        
        # Get final result if thread finished normally
        try:
            if not result_queue.empty():
                status, response, new_session_id = result_queue.get_nowait()
                
                # Clean up
                with self.monitor_lock:
                    if self.active_queries.get(query_id):
                        self.active_queries.pop(query_id, None)
                
                if status == "success":
                    return response, new_session_id
                elif status == "cancelled":
                    return None, None
                else:
                    raise Exception(response)
        except queue.Empty:
            pass
        
        # Clean up
        with self.monitor_lock:
            self.active_queries.pop(query_id, None)
        
        # Thread finished but no result - this shouldn't happen
        logger.error(f"Agent thread finished without result for query {query_id}")
        return None, None