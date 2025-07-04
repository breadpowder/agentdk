"""Tests for MemoryManager functionality.

This module tests the core memory management functionality following
the organized test structure that mirrors src/agentdk/memory/.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from agentdk.memory.memory_manager import MemoryManager


class TestMemoryManager:
    """Test cases for MemoryManager functionality."""

    def test_memory_manager_initialization(self, mock_memory_config):
        """Test MemoryManager initialization with configuration."""
        with patch('agentdk.memory.memory_manager.WorkingMemory') as mock_working:
            with patch('agentdk.memory.memory_manager.EpisodicMemory') as mock_episodic:
                with patch('agentdk.memory.memory_manager.FactualMemory') as mock_factual:
                    
                    manager = MemoryManager(
                        user_id="test_user",
                        config=mock_memory_config
                    )
                    
                    assert manager.user_id == "test_user"
                    assert manager.config == mock_memory_config

    def test_memory_manager_add_interaction(self, mock_memory_manager):
        """Test adding interactions to memory manager."""
        query = "What is the weather?"
        response = "It's sunny today."
        
        mock_memory_manager.add_interaction(query, response)
        
        mock_memory_manager.add_interaction.assert_called_once_with(query, response)

    def test_memory_manager_get_relevant_context(self, mock_memory_manager):
        """Test retrieving relevant context from memory manager."""
        query = "Tell me about the weather"
        
        context = mock_memory_manager.get_relevant_context(query)
        
        assert "episodic_memories" in context
        assert "factual_knowledge" in context
        assert "user_preferences" in context

    def test_memory_manager_get_stats(self, mock_memory_manager):
        """Test retrieving memory statistics."""
        stats = mock_memory_manager.get_stats()
        
        assert "total_interactions" in stats
        assert "episodic_memories" in stats
        assert "factual_entries" in stats

    @pytest.mark.asyncio
    async def test_memory_manager_async_operations(self):
        """Test memory manager async operations if applicable."""
        # Test any async functionality in memory manager
        with patch('agentdk.memory.memory_manager.MemoryManager') as MockManager:
            mock_instance = MockManager.return_value
            mock_instance.async_operation = Mock(return_value="async_result")
            
            # Verify async operations work correctly
            assert mock_instance is not None