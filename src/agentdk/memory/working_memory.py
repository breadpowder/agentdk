"""Working Memory implementation for AgentDK.

Working Memory provides short-term, session-aware context management with high accuracy.
It maintains conversation context within the current session and clears when session ends.
"""

import asyncio
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Deque
import json

from .base import BaseMemory, MemoryEntry, MemoryConfig
from ..core.logging_config import get_logger


class WorkingMemory(BaseMemory):
    """Working Memory for short-term session-aware context management.
    
    Features:
    - High-accuracy context preservation within session
    - Conversation buffer with configurable size
    - Session isolation and automatic cleanup
    - Fast in-memory operations
    """
    
    def __init__(self, user_id: Optional[str] = None, config: Optional[MemoryConfig] = None):
        """Initialize Working Memory.
        
        Args:
            user_id: Optional user identifier for scoping
            config: Optional memory configuration
        """
        super().__init__(user_id, config.to_dict() if config else None)
        self.logger = get_logger()
        self.memory_config = config or MemoryConfig()
        
        # Session management
        self.session_id = str(uuid.uuid4())
        self.session_start = datetime.now()
        self.last_activity = datetime.now()
        
        # Conversation buffer (deque for efficient operations)
        self.conversation_buffer: Deque[MemoryEntry] = deque(
            maxlen=self.memory_config.working_memory_size
        )
        
        # Current context tracking
        self.current_context: Dict[str, Any] = {}
        self.context_metadata: Dict[str, Any] = {}
        
        self.logger.info(f"WorkingMemory initialized for user {user_id}, session {self.session_id}")
    
    async def initialize(self) -> None:
        """Initialize working memory system."""
        if self._initialized:
            return
        
        self.logger.info("Initializing WorkingMemory")
        self._initialized = True
        self.logger.info("WorkingMemory initialization complete")
    
    async def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store content in working memory.
        
        Args:
            content: The content to store (typically conversation message)
            metadata: Optional metadata (role, timestamp, etc.)
            
        Returns:
            Unique identifier for the stored content
        """
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Update last activity
        self.last_activity = timestamp
        
        # Create memory entry
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            timestamp=timestamp,
            metadata=metadata or {},
            user_id=self.user_id
        )
        
        # Add to conversation buffer (automatically handles size limit)
        self.conversation_buffer.append(entry)
        
        # Update current context if this is a significant interaction
        if metadata and metadata.get('role') == 'user':
            self.current_context['last_user_query'] = content
            self.current_context['last_query_time'] = timestamp.isoformat()
        elif metadata and metadata.get('role') == 'assistant':
            self.current_context['last_assistant_response'] = content
            self.current_context['last_response_time'] = timestamp.isoformat()
        
        self.logger.debug(f"Stored content in WorkingMemory: {entry_id}")
        return entry_id
    
    async def retrieve(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Retrieve content from working memory.
        
        Args:
            query: Search query (can be "recent", "all", or specific content search)
            limit: Maximum number of entries to return
            
        Returns:
            List of matching memory entries
        """
        # Check session validity
        if not self._is_session_valid():
            await self._clear_expired_session()
            return []
        
        # Handle special queries
        if query.lower() == "recent":
            # Return most recent entries
            recent_entries = list(self.conversation_buffer)[-limit:]
            return recent_entries
        elif query.lower() == "all":
            # Return all entries in buffer
            return list(self.conversation_buffer)
        else:
            # Search for content matching query
            matching_entries = []
            for entry in self.conversation_buffer:
                if query.lower() in entry.content.lower():
                    matching_entries.append(entry)
                    if len(matching_entries) >= limit:
                        break
            return matching_entries
    
    async def update(self, entry_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update existing memory entry.
        
        Args:
            entry_id: Identifier of the entry to update
            content: New content
            metadata: Optional new metadata
            
        Returns:
            True if update was successful, False otherwise
        """
        for entry in self.conversation_buffer:
            if entry.id == entry_id:
                entry.content = content
                if metadata:
                    entry.metadata.update(metadata)
                entry.timestamp = datetime.now()  # Update timestamp
                self.last_activity = datetime.now()
                
                self.logger.debug(f"Updated WorkingMemory entry: {entry_id}")
                return True
        
        self.logger.warning(f"Entry not found for update: {entry_id}")
        return False
    
    async def delete(self, entry_id: str) -> bool:
        """Delete memory entry.
        
        Args:
            entry_id: Identifier of the entry to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        for i, entry in enumerate(self.conversation_buffer):
            if entry.id == entry_id:
                # Remove from deque by converting to list, removing, and recreating
                buffer_list = list(self.conversation_buffer)
                buffer_list.pop(i)
                self.conversation_buffer = deque(buffer_list, maxlen=self.memory_config.working_memory_size)
                
                self.logger.debug(f"Deleted WorkingMemory entry: {entry_id}")
                return True
        
        self.logger.warning(f"Entry not found for deletion: {entry_id}")
        return False
    
    async def clear(self, confirm: bool = False) -> bool:
        """Clear all working memory entries.
        
        Args:
            confirm: Safety confirmation flag
            
        Returns:
            True if clearing was successful, False otherwise
        """
        if not confirm:
            self.logger.warning("Clear operation requires confirmation")
            return False
        
        self.conversation_buffer.clear()
        self.current_context.clear()
        self.context_metadata.clear()
        
        # Reset session
        self.session_id = str(uuid.uuid4())
        self.session_start = datetime.now()
        self.last_activity = datetime.now()
        
        self.logger.info("WorkingMemory cleared and session reset")
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics.
        
        Returns:
            Dictionary containing memory usage statistics
        """
        session_duration = datetime.now() - self.session_start
        time_since_activity = datetime.now() - self.last_activity
        
        return {
            'type': 'working_memory',
            'session_id': self.session_id,
            'session_duration_seconds': session_duration.total_seconds(),
            'time_since_last_activity_seconds': time_since_activity.total_seconds(),
            'entries_count': len(self.conversation_buffer),
            'max_entries': self.memory_config.working_memory_size,
            'buffer_utilization': len(self.conversation_buffer) / self.memory_config.working_memory_size,
            'session_valid': self._is_session_valid(),
            'current_context_keys': list(self.current_context.keys()),
            'user_id': self.user_id
        }
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get current conversation context.
        
        Returns:
            Dictionary containing current context information
        """
        if not self._is_session_valid():
            return {}
        
        context = self.current_context.copy()
        context['session_id'] = self.session_id
        context['session_duration'] = (datetime.now() - self.session_start).total_seconds()
        context['recent_messages_count'] = len(self.conversation_buffer)
        
        return context
    
    def get_recent_conversation(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation messages.
        
        Args:
            limit: Maximum number of recent messages to return
            
        Returns:
            List of recent conversation entries as dictionaries
        """
        if not self._is_session_valid():
            return []
        
        recent_entries = list(self.conversation_buffer)[-limit:]
        return [entry.to_dict() for entry in recent_entries]
    
    def _is_session_valid(self) -> bool:
        """Check if current session is still valid.
        
        Returns:
            True if session is valid, False if expired
        """
        session_timeout = timedelta(seconds=self.memory_config.session_timeout)
        return (datetime.now() - self.last_activity) <= session_timeout
    
    async def _clear_expired_session(self) -> None:
        """Clear memory if session has expired."""
        if not self._is_session_valid():
            self.logger.info(f"Session {self.session_id} expired, clearing working memory")
            await self.clear(confirm=True)
    
    def start_new_session(self) -> str:
        """Start a new session, clearing current working memory.
        
        Returns:
            New session ID
        """
        old_session = self.session_id
        asyncio.create_task(self.clear(confirm=True))
        
        self.logger.info(f"Started new session {self.session_id}, previous session: {old_session}")
        return self.session_id
