"""Tests for agentdk.memory.working_memory module."""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from collections import deque
from unittest.mock import Mock, patch
from typing import Dict, Any

from agentdk.memory.working_memory import WorkingMemory
from agentdk.memory.base import MemoryConfig, MemoryEntry


class TestWorkingMemoryInitialization:
    """Test WorkingMemory initialization and configuration."""
    
    def test_init_default_config(self):
        """Test WorkingMemory initialization with default configuration."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            
            assert memory.user_id is None
            assert isinstance(memory.memory_config, MemoryConfig)
            assert memory.memory_config.working_memory_size == 10  # Default value
            assert isinstance(memory.session_id, str)
            assert isinstance(memory.session_start, datetime)
            assert isinstance(memory.last_activity, datetime)
            assert isinstance(memory.conversation_buffer, deque)
            assert memory.conversation_buffer.maxlen == 10
            assert memory.current_context == {}
            assert memory.context_metadata == {}
            assert not memory.is_initialized()
            
            # Verify logging
            mock_logger.info.assert_called_once()
            log_msg = mock_logger.info.call_args[0][0]
            assert "WorkingMemory initialized" in log_msg
            assert memory.session_id in log_msg
    
    def test_init_custom_config(self):
        """Test WorkingMemory initialization with custom configuration."""
        custom_config = MemoryConfig({
            'working_memory_size': 20,
            'session_timeout': 1800
        })
        
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(user_id="test_user", config=custom_config)
            
            assert memory.user_id == "test_user"
            assert memory.memory_config.working_memory_size == 20
            assert memory.memory_config.session_timeout == 1800
            assert memory.conversation_buffer.maxlen == 20
    
    def test_init_generates_unique_session_ids(self):
        """Test that multiple instances generate unique session IDs."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory1 = WorkingMemory()
            memory2 = WorkingMemory()
            
            assert memory1.session_id != memory2.session_id
            assert len(memory1.session_id) > 0
            assert len(memory2.session_id) > 0


class TestWorkingMemoryInitialize:
    """Test WorkingMemory initialization method."""
    
    @pytest.mark.asyncio
    async def test_initialize_first_time(self):
        """Test first-time initialization."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            assert not memory.is_initialized()
            
            await memory.initialize()
            
            assert memory.is_initialized()
            assert mock_logger.info.call_count >= 2  # Initialization messages
    
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self):
        """Test initialization when already initialized."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            await memory.initialize()
            
            # Clear previous calls
            mock_logger.reset_mock()
            
            # Initialize again
            await memory.initialize()
            
            # Should not log initialization messages again
            initialization_calls = [call for call in mock_logger.info.call_args_list 
                                  if "Initializing" in str(call) or "initialization complete" in str(call)]
            assert len(initialization_calls) == 0


class TestWorkingMemoryStore:
    """Test WorkingMemory store functionality."""
    
    @pytest.mark.asyncio
    async def test_store_basic_content(self):
        """Test storing basic content."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            entry_id = await memory.store("Test content")
            
            assert isinstance(entry_id, str)
            assert len(memory.conversation_buffer) == 1
            
            entry = memory.conversation_buffer[0]
            assert entry.id == entry_id
            assert entry.content == "Test content"
            assert entry.user_id is None
            assert isinstance(entry.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_store_with_metadata(self):
        """Test storing content with metadata."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            metadata = {"role": "user", "importance": 0.8}
            entry_id = await memory.store("User query", metadata)
            
            entry = memory.conversation_buffer[0]
            assert entry.metadata == metadata
    
    @pytest.mark.asyncio
    async def test_store_user_query_updates_context(self):
        """Test that storing user query updates current context."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            user_content = "What is the weather?"
            metadata = {"role": "user"}
            
            await memory.store(user_content, metadata)
            
            assert memory.current_context['last_user_query'] == user_content
            assert 'last_query_time' in memory.current_context
    
    @pytest.mark.asyncio
    async def test_store_assistant_response_updates_context(self):
        """Test that storing assistant response updates current context."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            assistant_content = "The weather is sunny."
            metadata = {"role": "assistant"}
            
            await memory.store(assistant_content, metadata)
            
            assert memory.current_context['last_assistant_response'] == assistant_content
            assert 'last_response_time' in memory.current_context
    
    @pytest.mark.asyncio
    async def test_store_updates_last_activity(self):
        """Test that storing content updates last activity timestamp."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            initial_activity = memory.last_activity
            
            # Add small delay to ensure timestamp difference
            await asyncio.sleep(0.01)
            await memory.store("Test content")
            
            assert memory.last_activity > initial_activity
    
    @pytest.mark.asyncio
    async def test_store_buffer_size_limit(self):
        """Test that buffer respects size limit."""
        config = MemoryConfig({'working_memory_size': 3})
        
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(config=config)
            await memory.initialize()
            
            # Store more entries than buffer size
            entry_ids = []
            for i in range(5):
                entry_id = await memory.store(f"Content {i}")
                entry_ids.append(entry_id)
            
            # Buffer should only contain last 3 entries
            assert len(memory.conversation_buffer) == 3
            
            # Check that the last 3 entries are preserved
            buffer_contents = [entry.content for entry in memory.conversation_buffer]
            assert buffer_contents == ["Content 2", "Content 3", "Content 4"]
    
    @pytest.mark.asyncio
    async def test_store_with_user_scoping(self):
        """Test storing content with user scoping."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(user_id="test_user")
            await memory.initialize()
            
            await memory.store("User-scoped content")
            
            entry = memory.conversation_buffer[0]
            assert entry.user_id == "test_user"


class TestWorkingMemoryRetrieve:
    """Test WorkingMemory retrieve functionality."""
    
    @pytest.mark.asyncio
    async def test_retrieve_recent_entries(self):
        """Test retrieving recent entries."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            # Store multiple entries
            for i in range(5):
                await memory.store(f"Content {i}")
            
            # Retrieve recent entries
            results = await memory.retrieve("recent", limit=3)
            
            assert len(results) == 3
            # Should return the last 3 entries
            contents = [entry.content for entry in results]
            assert contents == ["Content 2", "Content 3", "Content 4"]
    
    @pytest.mark.asyncio
    async def test_retrieve_all_entries(self):
        """Test retrieving all entries."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            # Store entries
            for i in range(3):
                await memory.store(f"Content {i}")
            
            results = await memory.retrieve("all")
            
            assert len(results) == 3
            contents = [entry.content for entry in results]
            assert contents == ["Content 0", "Content 1", "Content 2"]
    
    @pytest.mark.asyncio
    async def test_retrieve_content_search(self):
        """Test retrieving entries by content search."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            # Store diverse content
            await memory.store("Weather forecast")
            await memory.store("Stock prices")
            await memory.store("Weather update")
            await memory.store("News headlines")
            
            results = await memory.retrieve("weather")
            
            assert len(results) == 2
            contents = [entry.content for entry in results]
            assert "Weather forecast" in contents
            assert "Weather update" in contents
    
    @pytest.mark.asyncio
    async def test_retrieve_with_limit(self):
        """Test retrieve with limit parameter."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            # Store entries with similar content
            for i in range(5):
                await memory.store(f"Similar content {i}")
            
            results = await memory.retrieve("similar", limit=2)
            
            assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_retrieve_case_insensitive_search(self):
        """Test that content search is case-insensitive."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            await memory.store("UPPER case content")
            await memory.store("lower case content")
            
            results = await memory.retrieve("CASE")
            
            assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_retrieve_expired_session(self):
        """Test retrieve behavior with expired session."""
        config = MemoryConfig({'session_timeout': 1})  # 1 second timeout
        
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(config=config)
            await memory.initialize()
            
            await memory.store("Content before expiry")
            
            # Mock expired session
            with patch.object(memory, '_is_session_valid', return_value=False), \
                 patch.object(memory, '_clear_expired_session') as mock_clear:
                
                results = await memory.retrieve("content")
                
                assert len(results) == 0
                mock_clear.assert_called_once()


class TestWorkingMemoryUpdate:
    """Test WorkingMemory update functionality."""
    
    @pytest.mark.asyncio
    async def test_update_existing_entry(self):
        """Test updating existing entry."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            entry_id = await memory.store("Original content")
            
            success = await memory.update(entry_id, "Updated content", {"updated": True})
            
            assert success is True
            
            entry = memory.conversation_buffer[0]
            assert entry.content == "Updated content"
            assert entry.metadata["updated"] is True
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_entry(self):
        """Test updating non-existent entry."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            await memory.initialize()
            
            success = await memory.update("nonexistent_id", "New content")
            
            assert success is False
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_updates_timestamp_and_activity(self):
        """Test that update refreshes timestamp and last activity."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            entry_id = await memory.store("Original content")
            original_timestamp = memory.conversation_buffer[0].timestamp
            original_activity = memory.last_activity
            
            await asyncio.sleep(0.01)  # Small delay
            
            await memory.update(entry_id, "Updated content")
            
            updated_entry = memory.conversation_buffer[0]
            assert updated_entry.timestamp > original_timestamp
            assert memory.last_activity > original_activity


class TestWorkingMemoryDelete:
    """Test WorkingMemory delete functionality."""
    
    @pytest.mark.asyncio
    async def test_delete_existing_entry(self):
        """Test deleting existing entry."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            entry_id1 = await memory.store("Content 1")
            entry_id2 = await memory.store("Content 2")
            entry_id3 = await memory.store("Content 3")
            
            success = await memory.delete(entry_id2)
            
            assert success is True
            assert len(memory.conversation_buffer) == 2
            
            # Verify correct entry was deleted
            contents = [entry.content for entry in memory.conversation_buffer]
            assert "Content 1" in contents
            assert "Content 3" in contents
            assert "Content 2" not in contents
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry(self):
        """Test deleting non-existent entry."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            await memory.initialize()
            
            success = await memory.delete("nonexistent_id")
            
            assert success is False
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_preserves_buffer_maxlen(self):
        """Test that delete preserves buffer max length configuration."""
        config = MemoryConfig({'working_memory_size': 5})
        
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(config=config)
            await memory.initialize()
            
            entry_ids = []
            for i in range(3):
                entry_id = await memory.store(f"Content {i}")
                entry_ids.append(entry_id)
            
            await memory.delete(entry_ids[1])
            
            # Buffer should still respect maxlen
            assert memory.conversation_buffer.maxlen == 5
            assert len(memory.conversation_buffer) == 2


class TestWorkingMemoryClear:
    """Test WorkingMemory clear functionality."""
    
    @pytest.mark.asyncio
    async def test_clear_without_confirmation(self):
        """Test clear without confirmation."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            await memory.initialize()
            
            await memory.store("Content to clear")
            
            success = await memory.clear(confirm=False)
            
            assert success is False
            assert len(memory.conversation_buffer) == 1  # Content should remain
            mock_logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_with_confirmation(self):
        """Test clear with confirmation."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            await memory.initialize()
            
            await memory.store("Content to clear")
            memory.current_context['test_key'] = 'test_value'
            memory.context_metadata['meta_key'] = 'meta_value'
            
            old_session_id = memory.session_id
            old_session_start = memory.session_start
            
            success = await memory.clear(confirm=True)
            
            assert success is True
            assert len(memory.conversation_buffer) == 0
            assert memory.current_context == {}
            assert memory.context_metadata == {}
            
            # Should reset session
            assert memory.session_id != old_session_id
            assert memory.session_start > old_session_start
            
            mock_logger.info.assert_called()


class TestWorkingMemoryStats:
    """Test WorkingMemory statistics functionality."""
    
    @pytest.mark.asyncio
    async def test_get_stats_basic(self):
        """Test basic statistics retrieval."""
        config = MemoryConfig({'working_memory_size': 10})
        
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(user_id="stats_user", config=config)
            await memory.initialize()
            
            # Add some content
            for i in range(3):
                await memory.store(f"Content {i}")
            
            stats = await memory.get_stats()
            
            assert stats['type'] == 'working_memory'
            assert stats['session_id'] == memory.session_id
            assert stats['entries_count'] == 3
            assert stats['max_entries'] == 10
            assert stats['buffer_utilization'] == 0.3  # 3/10
            assert stats['session_valid'] is True
            assert stats['user_id'] == "stats_user"
            assert isinstance(stats['session_duration_seconds'], (int, float))
            assert isinstance(stats['time_since_last_activity_seconds'], (int, float))
    
    @pytest.mark.asyncio
    async def test_get_stats_current_context_keys(self):
        """Test that stats include current context keys."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            # Store user query to populate context
            await memory.store("User query", {"role": "user"})
            await memory.store("Assistant response", {"role": "assistant"})
            
            stats = await memory.get_stats()
            
            context_keys = stats['current_context_keys']
            assert 'last_user_query' in context_keys
            assert 'last_query_time' in context_keys
            assert 'last_assistant_response' in context_keys
            assert 'last_response_time' in context_keys


class TestWorkingMemoryContextMethods:
    """Test WorkingMemory context-related methods."""
    
    def test_get_current_context_valid_session(self):
        """Test getting current context with valid session."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            memory.current_context = {'test_key': 'test_value'}
            
            with patch.object(memory, '_is_session_valid', return_value=True):
                context = memory.get_current_context()
                
                assert context['test_key'] == 'test_value'
                assert context['session_id'] == memory.session_id
                assert 'session_duration' in context
                assert 'recent_messages_count' in context
    
    def test_get_current_context_invalid_session(self):
        """Test getting current context with invalid session."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            memory.current_context = {'test_key': 'test_value'}
            
            with patch.object(memory, '_is_session_valid', return_value=False):
                context = memory.get_current_context()
                
                assert context == {}
    
    def test_get_recent_conversation_valid_session(self):
        """Test getting recent conversation with valid session."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            
            # Add entries to buffer
            for i in range(5):
                entry = MemoryEntry(
                    id=f"id_{i}",
                    content=f"Content {i}",
                    timestamp=datetime.now(),
                    metadata={},
                    user_id=memory.user_id
                )
                memory.conversation_buffer.append(entry)
            
            with patch.object(memory, '_is_session_valid', return_value=True):
                conversation = memory.get_recent_conversation(limit=3)
                
                assert len(conversation) == 3
                # Should return last 3 entries
                assert conversation[0]['content'] == "Content 2"
                assert conversation[1]['content'] == "Content 3"
                assert conversation[2]['content'] == "Content 4"
    
    def test_get_recent_conversation_invalid_session(self):
        """Test getting recent conversation with invalid session."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            
            with patch.object(memory, '_is_session_valid', return_value=False):
                conversation = memory.get_recent_conversation()
                
                assert conversation == []


class TestWorkingMemorySessionManagement:
    """Test WorkingMemory session management functionality."""
    
    def test_is_session_valid_within_timeout(self):
        """Test session validity within timeout period."""
        config = MemoryConfig({'session_timeout': 3600})  # 1 hour
        
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(config=config)
            
            # Session should be valid immediately after creation
            assert memory._is_session_valid() is True
    
    def test_is_session_valid_expired(self):
        """Test session validity when expired."""
        config = MemoryConfig({'session_timeout': 1})  # 1 second
        
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(config=config)
            
            # Simulate expired session by setting old last_activity
            memory.last_activity = datetime.now() - timedelta(seconds=2)
            
            assert memory._is_session_valid() is False
    
    @pytest.mark.asyncio
    async def test_clear_expired_session(self):
        """Test clearing expired session."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            await memory.initialize()
            
            await memory.store("Content before expiry")
            old_session_id = memory.session_id
            
            # Mock expired session
            with patch.object(memory, '_is_session_valid', return_value=False):
                await memory._clear_expired_session()
                
                # Should clear memory and start new session
                assert len(memory.conversation_buffer) == 0
                assert memory.session_id != old_session_id
                
                # Should log session expiry
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                assert any("expired" in call for call in log_calls)
    
    def test_start_new_session(self):
        """Test starting a new session."""
        with patch('agentdk.memory.working_memory.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            memory = WorkingMemory()
            old_session_id = memory.session_id
            
            with patch('asyncio.create_task') as mock_create_task:
                new_session_id = memory.start_new_session()
                
                assert new_session_id != old_session_id
                assert memory.session_id == new_session_id
                
                # Should create task to clear memory
                mock_create_task.assert_called_once()
                
                # Should log session change
                mock_logger.info.assert_called()
                log_msg = mock_logger.info.call_args[0][0]
                assert "Started new session" in log_msg
                assert old_session_id in log_msg


class TestWorkingMemoryErrorScenarios:
    """Test WorkingMemory error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_operations_on_uninitialized_memory(self):
        """Test operations on uninitialized memory."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            
            # Should still work but may have different behavior
            entry_id = await memory.store("Content")
            assert entry_id is not None
            
            results = await memory.retrieve("content")
            assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_store_with_none_metadata(self):
        """Test storing content with None metadata."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            entry_id = await memory.store("Content", metadata=None)
            
            entry = memory.conversation_buffer[0]
            assert entry.metadata == {}
    
    @pytest.mark.asyncio
    async def test_update_with_none_metadata(self):
        """Test updating entry with None metadata."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            entry_id = await memory.store("Original", {"key": "value"})
            
            success = await memory.update(entry_id, "Updated", metadata=None)
            
            assert success is True
            entry = memory.conversation_buffer[0]
            assert entry.content == "Updated"
            # Original metadata should be preserved when None is passed
            assert entry.metadata == {"key": "value"}
    
    def test_buffer_operations_with_empty_buffer(self):
        """Test operations on empty conversation buffer."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            
            # Operations on empty buffer should handle gracefully
            context = memory.get_current_context()
            conversation = memory.get_recent_conversation()
            
            # Should not raise exceptions
            assert isinstance(context, dict)
            assert isinstance(conversation, list)
    
    @pytest.mark.asyncio
    async def test_concurrent_store_operations(self):
        """Test concurrent store operations."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory()
            await memory.initialize()
            
            # Create multiple concurrent store tasks
            tasks = []
            for i in range(10):
                task = memory.store(f"Concurrent content {i}")
                tasks.append(task)
            
            # Wait for all tasks to complete
            entry_ids = await asyncio.gather(*tasks)
            
            # All should succeed and have unique IDs
            assert len(entry_ids) == 10
            assert len(set(entry_ids)) == 10  # All unique
            assert len(memory.conversation_buffer) == 10


class TestWorkingMemoryIntegration:
    """Test WorkingMemory integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test a complete conversation flow."""
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(user_id="conversation_user")
            await memory.initialize()
            
            # Simulate a conversation
            await memory.store("Hello, what's the weather?", {"role": "user"})
            await memory.store("The weather is sunny today.", {"role": "assistant"})
            await memory.store("What about tomorrow?", {"role": "user"})
            await memory.store("Tomorrow will be cloudy.", {"role": "assistant"})
            
            # Check conversation state
            context = memory.get_current_context()
            assert context['last_user_query'] == "What about tomorrow?"
            assert context['last_assistant_response'] == "Tomorrow will be cloudy."
            
            # Get recent conversation
            recent = memory.get_recent_conversation()
            assert len(recent) == 4
            
            # Search for weather-related content
            weather_entries = await memory.retrieve("weather")
            assert len(weather_entries) == 1
            assert "sunny" in weather_entries[0].content
            
            # Get stats
            stats = await memory.get_stats()
            assert stats['entries_count'] == 4
            assert stats['user_id'] == "conversation_user"
    
    @pytest.mark.asyncio
    async def test_session_expiry_and_recovery(self):
        """Test session expiry and recovery behavior."""
        config = MemoryConfig({'session_timeout': 1})  # 1 second timeout
        
        with patch('agentdk.memory.working_memory.get_logger'):
            memory = WorkingMemory(config=config)
            await memory.initialize()
            
            # Store initial content
            await memory.store("Content before expiry")
            initial_count = len(memory.conversation_buffer)
            
            # Wait for session to expire
            await asyncio.sleep(1.1)
            
            # Trigger session check through retrieve
            results = await memory.retrieve("content")
            
            # Session should have been cleared
            assert len(results) == 0
            assert len(memory.conversation_buffer) == 0
            
            # Should be able to store new content
            await memory.store("Content after expiry")
            assert len(memory.conversation_buffer) == 1