"""Tests for agentdk.memory.base module."""

import pytest
import os
from datetime import datetime, timezone
from unittest.mock import patch
from typing import Dict, Any, List, Optional

from agentdk.memory.base import MemoryEntry, BaseMemory, MemoryConfig


class TestMemoryEntry:
    """Test the MemoryEntry dataclass."""
    
    def test_memory_entry_creation(self):
        """Test basic MemoryEntry creation."""
        timestamp = datetime.now(timezone.utc)
        metadata = {"source": "test", "importance": 0.8}
        
        entry = MemoryEntry(
            id="test_id",
            content="Test content",
            timestamp=timestamp,
            metadata=metadata,
            user_id="test_user"
        )
        
        assert entry.id == "test_id"
        assert entry.content == "Test content"
        assert entry.timestamp == timestamp
        assert entry.metadata == metadata
        assert entry.user_id == "test_user"
    
    def test_memory_entry_creation_without_user_id(self):
        """Test MemoryEntry creation without user_id."""
        timestamp = datetime.now(timezone.utc)
        metadata = {"type": "interaction"}
        
        entry = MemoryEntry(
            id="test_id",
            content="Test content",
            timestamp=timestamp,
            metadata=metadata
        )
        
        assert entry.user_id is None
    
    def test_to_dict(self):
        """Test MemoryEntry to_dict conversion."""
        timestamp = datetime(2023, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        metadata = {"type": "query", "confidence": 0.9}
        
        entry = MemoryEntry(
            id="entry_123",
            content="Sample memory content",
            timestamp=timestamp,
            metadata=metadata,
            user_id="user_456"
        )
        
        result = entry.to_dict()
        
        expected = {
            'id': 'entry_123',
            'content': 'Sample memory content',
            'timestamp': '2023-10-15T14:30:00+00:00',
            'metadata': {'type': 'query', 'confidence': 0.9},
            'user_id': 'user_456'
        }
        
        assert result == expected
    
    def test_to_dict_without_user_id(self):
        """Test to_dict with None user_id."""
        timestamp = datetime(2023, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        
        entry = MemoryEntry(
            id="entry_123",
            content="Content",
            timestamp=timestamp,
            metadata={},
            user_id=None
        )
        
        result = entry.to_dict()
        assert result['user_id'] is None
    
    def test_from_dict(self):
        """Test MemoryEntry from_dict creation."""
        data = {
            'id': 'entry_789',
            'content': 'Restored memory content',
            'timestamp': '2023-10-15T14:30:00+00:00',
            'metadata': {'category': 'factual'},
            'user_id': 'user_789'
        }
        
        entry = MemoryEntry.from_dict(data)
        
        assert entry.id == 'entry_789'
        assert entry.content == 'Restored memory content'
        assert entry.timestamp == datetime(2023, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        assert entry.metadata == {'category': 'factual'}
        assert entry.user_id == 'user_789'
    
    def test_from_dict_without_user_id(self):
        """Test from_dict without user_id field."""
        data = {
            'id': 'entry_000',
            'content': 'Content without user',
            'timestamp': '2023-10-15T14:30:00+00:00',
            'metadata': {}
        }
        
        entry = MemoryEntry.from_dict(data)
        
        assert entry.user_id is None
    
    def test_from_dict_with_explicit_none_user_id(self):
        """Test from_dict with explicit None user_id."""
        data = {
            'id': 'entry_none',
            'content': 'Content',
            'timestamp': '2023-10-15T14:30:00+00:00',
            'metadata': {},
            'user_id': None
        }
        
        entry = MemoryEntry.from_dict(data)
        
        assert entry.user_id is None
    
    def test_roundtrip_conversion(self):
        """Test that to_dict and from_dict are inverses."""
        original_timestamp = datetime(2023, 10, 15, 14, 30, 0, tzinfo=timezone.utc)
        original_entry = MemoryEntry(
            id="roundtrip_test",
            content="Original content",
            timestamp=original_timestamp,
            metadata={"test": True, "number": 42},
            user_id="roundtrip_user"
        )
        
        # Convert to dict and back
        dict_form = original_entry.to_dict()
        restored_entry = MemoryEntry.from_dict(dict_form)
        
        # Verify all fields match
        assert restored_entry.id == original_entry.id
        assert restored_entry.content == original_entry.content
        assert restored_entry.timestamp == original_entry.timestamp
        assert restored_entry.metadata == original_entry.metadata
        assert restored_entry.user_id == original_entry.user_id
    
    def test_timestamp_iso_format_handling(self):
        """Test various ISO timestamp formats."""
        # Test with microseconds
        data_with_microseconds = {
            'id': 'micro_test',
            'content': 'Content',
            'timestamp': '2023-10-15T14:30:00.123456+00:00',
            'metadata': {}
        }
        
        entry = MemoryEntry.from_dict(data_with_microseconds)
        assert entry.timestamp.microsecond == 123456
        
        # Test without timezone
        data_no_tz = {
            'id': 'no_tz_test',
            'content': 'Content',
            'timestamp': '2023-10-15T14:30:00',
            'metadata': {}
        }
        
        entry_no_tz = MemoryEntry.from_dict(data_no_tz)
        assert entry_no_tz.timestamp.year == 2023
        assert entry_no_tz.timestamp.month == 10
        assert entry_no_tz.timestamp.day == 15


class ConcreteMemory(BaseMemory):
    """Concrete implementation of BaseMemory for testing."""
    
    def __init__(self, user_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(user_id, config)
        self.storage = {}
        self.entry_counter = 0
    
    async def initialize(self) -> None:
        """Initialize the memory system."""
        self._initialized = True
    
    async def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store content in memory."""
        self.entry_counter += 1
        entry_id = f"entry_{self.entry_counter}"
        
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
            user_id=self.user_id
        )
        
        self.storage[entry_id] = entry
        return entry_id
    
    async def retrieve(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Retrieve content from memory."""
        # Simple search implementation for testing
        matches = []
        for entry in self.storage.values():
            if query.lower() in entry.content.lower():
                matches.append(entry)
                if len(matches) >= limit:
                    break
        return matches
    
    async def update(self, entry_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update existing memory entry."""
        if entry_id not in self.storage:
            return False
        
        entry = self.storage[entry_id]
        entry.content = content
        if metadata is not None:
            entry.metadata = metadata
        return True
    
    async def delete(self, entry_id: str) -> bool:
        """Delete memory entry."""
        if entry_id not in self.storage:
            return False
        del self.storage[entry_id]
        return True
    
    async def clear(self, confirm: bool = False) -> bool:
        """Clear all memory entries."""
        if not confirm:
            return False
        self.storage.clear()
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "total_entries": len(self.storage),
            "user_id": self.user_id,
            "initialized": self._initialized
        }


class TestBaseMemory:
    """Test the BaseMemory abstract base class."""
    
    def test_base_memory_initialization_defaults(self):
        """Test BaseMemory initialization with default values."""
        memory = ConcreteMemory()
        
        assert memory.user_id is None
        assert memory.config == {}
        assert not memory.is_initialized()
    
    def test_base_memory_initialization_with_params(self):
        """Test BaseMemory initialization with parameters."""
        config = {"param1": "value1", "param2": 42}
        memory = ConcreteMemory(user_id="test_user", config=config)
        
        assert memory.user_id == "test_user"
        assert memory.config == config
        assert not memory.is_initialized()
    
    @pytest.mark.asyncio
    async def test_initialization_changes_status(self):
        """Test that initialization changes the status."""
        memory = ConcreteMemory()
        
        assert not memory.is_initialized()
        await memory.initialize()
        assert memory.is_initialized()
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        """Test basic store and retrieve functionality."""
        memory = ConcreteMemory()
        await memory.initialize()
        
        # Store content
        entry_id = await memory.store("Test content", {"category": "test"})
        assert entry_id is not None
        
        # Retrieve content
        results = await memory.retrieve("Test")
        assert len(results) == 1
        assert results[0].content == "Test content"
        assert results[0].metadata["category"] == "test"
    
    @pytest.mark.asyncio
    async def test_update_existing_entry(self):
        """Test updating existing entry."""
        memory = ConcreteMemory()
        await memory.initialize()
        
        # Store and update
        entry_id = await memory.store("Original content")
        success = await memory.update(entry_id, "Updated content", {"updated": True})
        
        assert success is True
        
        # Verify update
        results = await memory.retrieve("Updated")
        assert len(results) == 1
        assert results[0].content == "Updated content"
        assert results[0].metadata["updated"] is True
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_entry(self):
        """Test updating non-existent entry."""
        memory = ConcreteMemory()
        await memory.initialize()
        
        success = await memory.update("nonexistent_id", "New content")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_delete_existing_entry(self):
        """Test deleting existing entry."""
        memory = ConcreteMemory()
        await memory.initialize()
        
        # Store and delete
        entry_id = await memory.store("Content to delete")
        success = await memory.delete(entry_id)
        
        assert success is True
        
        # Verify deletion
        results = await memory.retrieve("Content to delete")
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry(self):
        """Test deleting non-existent entry."""
        memory = ConcreteMemory()
        await memory.initialize()
        
        success = await memory.delete("nonexistent_id")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_clear_without_confirmation(self):
        """Test clearing without confirmation."""
        memory = ConcreteMemory()
        await memory.initialize()
        
        # Store some content
        await memory.store("Content 1")
        await memory.store("Content 2")
        
        # Try to clear without confirmation
        success = await memory.clear(confirm=False)
        assert success is False
        
        # Verify content still exists
        stats = await memory.get_stats()
        assert stats["total_entries"] > 0
    
    @pytest.mark.asyncio
    async def test_clear_with_confirmation(self):
        """Test clearing with confirmation."""
        memory = ConcreteMemory()
        await memory.initialize()
        
        # Store some content
        await memory.store("Content 1")
        await memory.store("Content 2")
        
        # Clear with confirmation
        success = await memory.clear(confirm=True)
        assert success is True
        
        # Verify content was cleared
        stats = await memory.get_stats()
        assert stats["total_entries"] == 0
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test get_stats functionality."""
        memory = ConcreteMemory(user_id="stats_user")
        await memory.initialize()
        
        # Store some content
        await memory.store("Content 1")
        await memory.store("Content 2")
        
        stats = await memory.get_stats()
        
        assert stats["total_entries"] == 2
        assert stats["user_id"] == "stats_user"
        assert stats["initialized"] is True
    
    @pytest.mark.asyncio
    async def test_retrieve_with_limit(self):
        """Test retrieve with limit parameter."""
        memory = ConcreteMemory()
        await memory.initialize()
        
        # Store multiple entries with same keyword
        for i in range(5):
            await memory.store(f"Test content {i}")
        
        # Retrieve with limit
        results = await memory.retrieve("Test", limit=3)
        assert len(results) <= 3
    
    @pytest.mark.asyncio
    async def test_user_scoping(self):
        """Test that user_id is properly set in stored entries."""
        memory = ConcreteMemory(user_id="scoped_user")
        await memory.initialize()
        
        entry_id = await memory.store("User-scoped content")
        results = await memory.retrieve("User-scoped")
        
        assert len(results) == 1
        assert results[0].user_id == "scoped_user"


class TestMemoryConfig:
    """Test the MemoryConfig class."""
    
    def test_default_configuration(self):
        """Test MemoryConfig with default values."""
        config = MemoryConfig()
        
        assert config.working_memory_size == 10
        assert config.session_timeout == 3600
        assert config.compression_threshold == 1000
        assert config.max_episodic_entries == 1000
        assert config.preference_categories == ['ui', 'agent', 'system']
        assert config.storage_path == '/tmp/memory_data/agentdk_memory.db'
        assert config.backup_enabled is True
        assert config.multi_user_enabled is False
        assert config.default_user_id == 'default'
    
    def test_custom_configuration(self):
        """Test MemoryConfig with custom values."""
        custom_config = {
            'working_memory_size': 20,
            'session_timeout': 7200,
            'compression_threshold': 500,
            'max_episodic_entries': 2000,
            'preference_categories': ['custom', 'categories'],
            'storage_path': '/custom/path/memory.db',
            'backup_enabled': False,
            'multi_user_enabled': True,
            'default_user_id': 'custom_default'
        }
        
        config = MemoryConfig(custom_config)
        
        assert config.working_memory_size == 20
        assert config.session_timeout == 7200
        assert config.compression_threshold == 500
        assert config.max_episodic_entries == 2000
        assert config.preference_categories == ['custom', 'categories']
        assert config.storage_path == '/custom/path/memory.db'
        assert config.backup_enabled is False
        assert config.multi_user_enabled is True
        assert config.default_user_id == 'custom_default'
    
    def test_partial_configuration(self):
        """Test MemoryConfig with partial custom values."""
        partial_config = {
            'working_memory_size': 15,
            'storage_path': '/new/path/memory.db'
        }
        
        config = MemoryConfig(partial_config)
        
        # Custom values
        assert config.working_memory_size == 15
        assert config.storage_path == '/new/path/memory.db'
        
        # Default values for unspecified options
        assert config.session_timeout == 3600
        assert config.compression_threshold == 1000
        assert config.backup_enabled is True
    
    def test_to_dict(self):
        """Test MemoryConfig to_dict conversion."""
        custom_config = {
            'working_memory_size': 25,
            'session_timeout': 1800,
            'backup_enabled': False
        }
        
        config = MemoryConfig(custom_config)
        result = config.to_dict()
        
        expected_keys = {
            'working_memory_size', 'session_timeout', 'compression_threshold',
            'max_episodic_entries', 'preference_categories', 'storage_path',
            'backup_enabled', 'multi_user_enabled', 'default_user_id'
        }
        
        assert set(result.keys()) == expected_keys
        assert result['working_memory_size'] == 25
        assert result['session_timeout'] == 1800
        assert result['backup_enabled'] is False
        
        # Check that defaults are included
        assert result['compression_threshold'] == 1000
        assert result['multi_user_enabled'] is False
    
    @patch.dict(os.environ, {
        'AGENTDK_WORKING_MEMORY_SIZE': '30',
        'AGENTDK_SESSION_TIMEOUT': '5400',
        'AGENTDK_COMPRESSION_THRESHOLD': '750',
        'AGENTDK_MAX_EPISODIC_ENTRIES': '1500',
        'AGENTDK_PREFERENCE_CATEGORIES': 'env,test,categories',
        'AGENTDK_MEMORY_STORAGE_PATH': '/env/path/memory.db',
        'AGENTDK_MEMORY_BACKUP_ENABLED': 'false',
        'AGENTDK_MULTI_USER_ENABLED': 'true',
        'AGENTDK_DEFAULT_USER_ID': 'env_user'
    })
    def test_from_env_all_variables(self):
        """Test MemoryConfig.from_env with all environment variables set."""
        config = MemoryConfig.from_env()
        
        assert config.working_memory_size == 30
        assert config.session_timeout == 5400
        assert config.compression_threshold == 750
        assert config.max_episodic_entries == 1500
        assert config.preference_categories == ['env', 'test', 'categories']
        assert config.storage_path == '/env/path/memory.db'
        assert config.backup_enabled is False
        assert config.multi_user_enabled is True
        assert config.default_user_id == 'env_user'
    
    @patch.dict(os.environ, {
        'AGENTDK_WORKING_MEMORY_SIZE': '50',
        'AGENTDK_MEMORY_BACKUP_ENABLED': 'True'  # Test case variation
    }, clear=True)
    def test_from_env_partial_variables(self):
        """Test MemoryConfig.from_env with partial environment variables."""
        config = MemoryConfig.from_env()
        
        # Environment variables
        assert config.working_memory_size == 50
        assert config.backup_enabled is True  # 'True' should be parsed as true
        
        # Defaults for missing variables
        assert config.session_timeout == 3600
        assert config.compression_threshold == 1000
        assert config.storage_path == './agentdk_memory.db'
        assert config.multi_user_enabled is False
        assert config.default_user_id == 'default'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_no_variables(self):
        """Test MemoryConfig.from_env with no environment variables."""
        config = MemoryConfig.from_env()
        
        # Should use all defaults
        assert config.working_memory_size == 10
        assert config.session_timeout == 3600
        assert config.compression_threshold == 1000
        assert config.max_episodic_entries == 1000
        assert config.preference_categories == ['ui', 'agent', 'system']
        assert config.storage_path == './agentdk_memory.db'
        assert config.backup_enabled is True
        assert config.multi_user_enabled is False
        assert config.default_user_id == 'default'
    
    @patch.dict(os.environ, {
        'AGENTDK_MEMORY_BACKUP_ENABLED': 'FALSE',
        'AGENTDK_MULTI_USER_ENABLED': 'yes'  # Not 'true', should be false
    })
    def test_boolean_parsing(self):
        """Test boolean parsing from environment variables."""
        config = MemoryConfig.from_env()
        
        assert config.backup_enabled is False  # 'FALSE' -> false
        assert config.multi_user_enabled is False  # 'yes' -> false (only 'true' is true)
    
    def test_config_immutability_protection(self):
        """Test that modifying original config dict doesn't affect MemoryConfig."""
        original_config = {'working_memory_size': 100}
        config = MemoryConfig(original_config)
        
        # Modify original dict
        original_config['working_memory_size'] = 200
        
        # MemoryConfig should not be affected
        assert config.working_memory_size == 100