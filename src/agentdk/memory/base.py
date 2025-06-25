"""Base classes and interfaces for the AgentDK memory system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class MemoryEntry:
    """Base class for all memory entries.
    
    Attributes:
        id: Unique identifier for the memory entry
        content: The actual memory content
        timestamp: When this memory was created
        metadata: Additional metadata about the memory
        user_id: User scope for multi-user support
    """
    id: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory entry to dictionary format.
        
        Returns:
            Dictionary representation of the memory entry
        """
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'user_id': self.user_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create memory entry from dictionary.
        
        Args:
            data: Dictionary containing memory entry data
            
        Returns:
            MemoryEntry instance
        """
        return cls(
            id=data['id'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data['metadata'],
            user_id=data.get('user_id')
        )


class BaseMemory(ABC):
    """Abstract base class for all memory types.
    
    Defines the common interface that all memory implementations must follow.
    """
    
    def __init__(self, user_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize base memory.
        
        Args:
            user_id: Optional user identifier for scoping
            config: Optional configuration dictionary
        """
        self.user_id = user_id
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the memory system.
        
        This method should set up any required resources, connections,
        or data structures needed for the memory to function.
        """
        pass
    
    @abstractmethod
    async def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store content in memory.
        
        Args:
            content: The content to store
            metadata: Optional metadata about the content
            
        Returns:
            Unique identifier for the stored content
        """
        pass
    
    @abstractmethod
    async def retrieve(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Retrieve content from memory.
        
        Args:
            query: Search query or identifier
            limit: Maximum number of entries to return
            
        Returns:
            List of matching memory entries
        """
        pass
    
    @abstractmethod
    async def update(self, entry_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update existing memory entry.
        
        Args:
            entry_id: Identifier of the entry to update
            content: New content
            metadata: Optional new metadata
            
        Returns:
            True if update was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete memory entry.
        
        Args:
            entry_id: Identifier of the entry to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear(self, confirm: bool = False) -> bool:
        """Clear all memory entries.
        
        Args:
            confirm: Safety confirmation flag
            
        Returns:
            True if clearing was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics.
        
        Returns:
            Dictionary containing memory usage statistics
        """
        pass
    
    def is_initialized(self) -> bool:
        """Check if memory is initialized.
        
        Returns:
            True if memory is initialized, False otherwise
        """
        return self._initialized


class MemoryConfig:
    """Configuration class for memory system settings."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize memory configuration.
        
        Args:
            config_dict: Optional configuration dictionary
        """
        self.config = config_dict or {}
        
        # Working Memory Configuration
        self.working_memory_size = self.config.get('working_memory_size', 10)
        self.session_timeout = self.config.get('session_timeout', 3600)  # 1 hour
        
        # Episodic Memory Configuration
        self.compression_threshold = self.config.get('compression_threshold', 1000)
        self.max_episodic_entries = self.config.get('max_episodic_entries', 1000)
        
        # Factual Memory Configuration
        self.preference_categories = self.config.get('preference_categories', ['ui', 'agent', 'system'])
        
        # Storage Configuration
        self.storage_path = self.config.get('storage_path', '/tmp/memory_data/agentdk_memory.db')
        self.backup_enabled = self.config.get('backup_enabled', True)
        
        # User Scoping
        self.multi_user_enabled = self.config.get('multi_user_enabled', False)
        self.default_user_id = self.config.get('default_user_id', 'default')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            'working_memory_size': self.working_memory_size,
            'session_timeout': self.session_timeout,
            'compression_threshold': self.compression_threshold,
            'max_episodic_entries': self.max_episodic_entries,
            'preference_categories': self.preference_categories,
            'storage_path': self.storage_path,
            'backup_enabled': self.backup_enabled,
            'multi_user_enabled': self.multi_user_enabled,
            'default_user_id': self.default_user_id
        }
    
    @classmethod
    def from_env(cls) -> 'MemoryConfig':
        """Create configuration from environment variables.
        
        Returns:
            MemoryConfig instance with environment-based settings
        """
        import os
        
        config = {
            'working_memory_size': int(os.getenv('AGENTDK_WORKING_MEMORY_SIZE', '10')),
            'session_timeout': int(os.getenv('AGENTDK_SESSION_TIMEOUT', '3600')),
            'compression_threshold': int(os.getenv('AGENTDK_COMPRESSION_THRESHOLD', '1000')),
            'max_episodic_entries': int(os.getenv('AGENTDK_MAX_EPISODIC_ENTRIES', '1000')),
            'preference_categories': os.getenv('AGENTDK_PREFERENCE_CATEGORIES', 'ui,agent,system').split(','),
            'storage_path': os.getenv('AGENTDK_MEMORY_STORAGE_PATH', './agentdk_memory.db'),
            'backup_enabled': os.getenv('AGENTDK_MEMORY_BACKUP_ENABLED', 'true').lower() == 'true',
            'multi_user_enabled': os.getenv('AGENTDK_MULTI_USER_ENABLED', 'false').lower() == 'true',
            'default_user_id': os.getenv('AGENTDK_DEFAULT_USER_ID', 'default')
        }
        
        return cls(config)
