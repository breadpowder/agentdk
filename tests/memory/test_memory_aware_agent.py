"""Tests for MemoryAwareAgent interface."""

import pytest
from typing import Any
from unittest.mock import patch, MagicMock

from agentdk.memory import MemoryAwareAgent


class MockMemoryAgent(MemoryAwareAgent):
    """Test implementation of MemoryAwareAgent for testing."""
    
    def __call__(self, query: str) -> str:
        """Test implementation of query processing."""
        enhanced_input = self.process_with_memory(query)
        response = f"Test response to: {query}"
        return self.finalize_with_memory(query, response)
    
    def create_workflow(self, *args, **kwargs) -> Any:
        """Test implementation of workflow creation."""
        return None


class TestMemoryAwareAgent:
    """Test cases for MemoryAwareAgent interface."""
    
    def test_memory_aware_agent_without_memory(self):
        """Test MemoryAwareAgent with memory disabled."""
        agent = MockMemoryAgent(memory=False)
        
        assert agent.memory is None
        assert agent.memory_tools is None
        
        # Test fallback methods
        assert agent.memory_tool("stats") == "❌ Memory system not available"
        assert agent.set_preference("ui", "test", "value") == "❌ Memory system not available"
        assert agent.get_preference("ui", "test", "default") == "default"
        assert agent.get_memory_stats() == "❌ Memory system not available"
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    @patch('agentdk.memory.memory_aware_agent.MemoryTools')
    def test_memory_aware_agent_with_memory(self, mock_memory_tools, mock_memory_manager):
        """Test MemoryAwareAgent with memory enabled."""
        # Setup mocks
        mock_memory = MagicMock()
        mock_memory_manager.return_value = mock_memory
        mock_tools = MagicMock()
        mock_memory_tools.return_value = mock_tools
        
        agent = MockMemoryAgent(memory=True, user_id="test_user")
        
        # Verify memory components were created
        mock_memory_manager.assert_called_once_with(
            config=None,
            user_id="test_user"
        )
        mock_memory_tools.assert_called_once_with(mock_memory)
        
        assert agent.memory == mock_memory
        assert agent.memory_tools == mock_tools
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    def test_process_with_memory(self, mock_memory_manager):
        """Test process_with_memory method."""
        mock_memory = MagicMock()
        mock_memory.get_llm_context.return_value = "test context"
        mock_memory_manager.return_value = mock_memory
        
        agent = MockMemoryAgent(memory=True)
        
        result = agent.process_with_memory("test query")
        
        expected = {
            "messages": [{"role": "user", "content": "test query"}],
            "memory_context": "test context"
        }
        assert result == expected
        mock_memory.get_llm_context.assert_called_once_with("test query")
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    def test_process_with_memory_no_context(self, mock_memory_manager):
        """Test process_with_memory when no context is available."""
        mock_memory = MagicMock()
        mock_memory.get_llm_context.return_value = None
        mock_memory_manager.return_value = mock_memory
        
        agent = MockMemoryAgent(memory=True)
        
        result = agent.process_with_memory("test query")
        
        expected = {
            "messages": [{"role": "user", "content": "test query"}]
        }
        assert result == expected
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    def test_finalize_with_memory(self, mock_memory_manager):
        """Test finalize_with_memory method."""
        mock_memory = MagicMock()
        mock_memory_manager.return_value = mock_memory
        
        agent = MockMemoryAgent(memory=True)
        
        result = agent.finalize_with_memory("test query", "test response")
        
        assert result == "test response"
        mock_memory.store_interaction.assert_called_once_with("test query", "test response")
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    def test_get_memory_aware_prompt(self, mock_memory_manager):
        """Test get_memory_aware_prompt method."""
        mock_memory = MagicMock()
        mock_memory_manager.return_value = mock_memory
        
        agent = MockMemoryAgent(memory=True)
        
        base_prompt = "Base prompt"
        enhanced_prompt = agent.get_memory_aware_prompt(base_prompt)
        
        assert base_prompt in enhanced_prompt
        assert "MEMORY AWARENESS:" in enhanced_prompt
        assert "USER PREFERENCE SUPPORT:" in enhanced_prompt
    
    def test_get_memory_aware_prompt_without_memory(self):
        """Test get_memory_aware_prompt without memory."""
        agent = MockMemoryAgent(memory=False)
        
        base_prompt = "Base prompt"
        enhanced_prompt = agent.get_memory_aware_prompt(base_prompt)
        
        assert enhanced_prompt == base_prompt
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    @patch('agentdk.memory.memory_aware_agent.MemoryTools')
    def test_memory_tool_method(self, mock_memory_tools, mock_memory_manager):
        """Test memory_tool method."""
        mock_memory = MagicMock()
        mock_memory_manager.return_value = mock_memory
        mock_tools = MagicMock()
        mock_tools.execute.return_value = "test result"
        mock_memory_tools.return_value = mock_tools
        
        agent = MockMemoryAgent(memory=True)
        
        result = agent.memory_tool("stats")
        
        assert result == "test result"
        mock_tools.execute.assert_called_once_with("stats")
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    def test_preference_methods(self, mock_memory_manager):
        """Test preference management methods."""
        mock_memory = MagicMock()
        mock_memory.set_preference.return_value = None
        mock_memory.get_preference.return_value = "test_value"
        mock_memory_manager.return_value = mock_memory
        
        agent = MockMemoryAgent(memory=True)
        
        # Test set_preference
        result = agent.set_preference("ui", "test", "value")
        assert "✅ Preference set: ui.test = value" in result
        mock_memory.set_preference.assert_called_once_with("ui", "test", "value")
        
        # Test get_preference
        value = agent.get_preference("ui", "test", "default")
        assert value == "test_value"
        mock_memory.get_preference.assert_called_once_with("ui", "test", "default")
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    def test_exception_handling(self, mock_memory_manager):
        """Test exception handling in memory operations."""
        mock_memory = MagicMock()
        mock_memory.store_interaction.side_effect = Exception("Test error")
        mock_memory_manager.return_value = mock_memory
        
        agent = MockMemoryAgent(memory=True)
        
        # Should not raise exception, just print warning
        result = agent.finalize_with_memory("test", "response")
        assert result == "response"
    
    @patch('agentdk.memory.memory_aware_agent.MemoryManager')
    def test_full_workflow(self, mock_memory_manager):
        """Test complete workflow with memory."""
        mock_memory = MagicMock()
        mock_memory.get_llm_context.return_value = {"working": {"test": "context"}}
        mock_memory_manager.return_value = mock_memory
        
        agent = MockMemoryAgent(memory=True, user_id="workflow_test")
        
        # Process a query
        response = agent("Hello world")
        
        # Verify the workflow
        assert response == "Test response to: Hello world"
        mock_memory.get_llm_context.assert_called_once_with("Hello world")
        mock_memory.store_interaction.assert_called_once_with("Hello world", "Test response to: Hello world") 