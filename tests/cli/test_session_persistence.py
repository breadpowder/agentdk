"""Tests for session persistence functionality."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from agentdk.agent.session_manager import SessionManager
from agentdk.memory.memory_aware_agent import MemoryAwareAgent


@pytest.fixture
def temp_session_dir():
    """Create a temporary session directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def session_manager(temp_session_dir):
    """Create a SessionManager instance for testing."""
    return SessionManager("test_agent", session_dir=temp_session_dir)


@pytest.fixture
def mock_memory_aware_agent():
    """Create a mock MemoryAwareAgent for testing."""
    class MockAgent(MemoryAwareAgent):
        def __init__(self):
            self.memory = Mock()
            self.memory.store_interaction = Mock()
            self.memory.working_memory = Mock()
            self.memory.working_memory.get_context = Mock(return_value=[
                {"content": "User: test query"},
                {"content": "Assistant: test response"}
            ])
        
        def __call__(self, query: str) -> str:
            return f"Response to: {query}"
        
        def create_workflow(self, *args, **kwargs):
            return Mock()
    
    return MockAgent()


class TestSessionManager:
    """Test SessionManager functionality."""
    
    @pytest.mark.asyncio
    async def test_start_new_session(self, session_manager):
        """Test creating a new session."""
        await session_manager.start_new_session()
        
        assert session_manager.current_session["agent_name"] == "test_agent"
        assert session_manager.current_session["format_version"] == "1.0"
        assert session_manager.current_session["interactions"] == []
        assert session_manager.current_session["memory_state"] == {}
        assert "created_at" in session_manager.current_session
        assert "last_updated" in session_manager.current_session
    
    @pytest.mark.asyncio
    async def test_save_interaction(self, session_manager):
        """Test saving interactions to session."""
        await session_manager.start_new_session()
        
        memory_state = {"working_memory": [{"content": "test"}]}
        await session_manager.save_interaction("test query", "test response", memory_state)
        
        interactions = session_manager.current_session["interactions"]
        assert len(interactions) == 1
        assert interactions[0]["user_input"] == "test query"
        assert interactions[0]["agent_response"] == "test response"
        assert "timestamp" in interactions[0]
        assert session_manager.current_session["memory_state"] == memory_state
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, session_manager):
        """Test loading a session that doesn't exist."""
        result = await session_manager.load_session()
        
        assert result is False
        assert session_manager.current_session["agent_name"] == "test_agent"
        assert session_manager.current_session["interactions"] == []
    
    @pytest.mark.asyncio
    async def test_load_existing_session(self, session_manager):
        """Test loading an existing session."""
        # Create and save a session first
        await session_manager.start_new_session()
        await session_manager.save_interaction("test query", "test response")
        
        # Create new manager instance and load session
        new_manager = SessionManager("test_agent", session_dir=session_manager.session_dir)
        result = await new_manager.load_session()
        
        assert result is True
        assert len(new_manager.current_session["interactions"]) == 1
        assert new_manager.current_session["interactions"][0]["user_input"] == "test query"
    
    @pytest.mark.asyncio
    async def test_corrupted_session_handling(self, session_manager):
        """Test handling of corrupted session files."""
        # Create a corrupted session file
        session_manager.session_file.write_text("invalid json {")
        
        result = await session_manager.load_session()
        
        assert result is False
        # Should create a backup and start fresh
        assert session_manager.current_session["interactions"] == []
    
    def test_validate_session_format(self, session_manager):
        """Test session format validation."""
        # No file exists
        assert not session_manager._validate_session_format()
        
        # Valid session file
        valid_session = {
            "agent_name": "test_agent",
            "created_at": datetime.now().isoformat(),
            "interactions": [],
            "format_version": "1.0"
        }
        session_manager.session_file.write_text(json.dumps(valid_session))
        assert session_manager._validate_session_format()
        
        # Invalid session file (missing required fields)
        invalid_session = {"agent_name": "test_agent"}
        session_manager.session_file.write_text(json.dumps(invalid_session))
        assert not session_manager._validate_session_format()
    
    def test_get_session_info(self, session_manager):
        """Test getting session information."""
        # No session exists
        info = session_manager.get_session_info()
        assert not info["exists"]
        assert info["agent_name"] == "test_agent"
        
        # Create valid session
        valid_session = {
            "agent_name": "test_agent",
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T01:00:00",
            "format_version": "1.0",
            "interactions": [{"user_input": "test", "agent_response": "response"}],
            "memory_state": {"test": "data"}
        }
        session_manager.session_file.write_text(json.dumps(valid_session))
        
        info = session_manager.get_session_info()
        assert info["exists"]
        assert info["agent_name"] == "test_agent"
        assert info["interaction_count"] == 1
        assert info["has_memory_state"] is True
        assert info["format_version"] == "1.0"
    
    def test_has_previous_session(self, session_manager):
        """Test checking for previous session existence."""
        assert not session_manager.has_previous_session()
        
        # Create valid session
        valid_session = {
            "agent_name": "test_agent",
            "created_at": datetime.now().isoformat(),
            "interactions": []
        }
        session_manager.session_file.write_text(json.dumps(valid_session))
        assert session_manager.has_previous_session()
    
    def test_get_session_context(self, session_manager):
        """Test getting session context for agent restoration."""
        session_manager.current_session = {
            "interactions": [
                {"user_input": "query1", "agent_response": "response1"},
                {"user_input": "query2", "agent_response": "response2"}
            ]
        }
        
        context = session_manager.get_session_context()
        assert len(context) == 2
        assert context[0]["user_input"] == "query1"
        assert context[1]["user_input"] == "query2"


class TestMemoryAwareAgentSessionIntegration:
    """Test integration between MemoryAwareAgent and session management."""
    
    def test_restore_from_session(self, mock_memory_aware_agent):
        """Test restoring agent state from session context."""
        session_context = [
            {"user_input": "test query 1", "agent_response": "test response 1"},
            {"user_input": "test query 2", "agent_response": "test response 2"}
        ]
        
        result = mock_memory_aware_agent.restore_from_session(session_context)
        
        assert result is True
        # Verify interactions were stored in memory
        assert mock_memory_aware_agent.memory.store_interaction.call_count == 2
        mock_memory_aware_agent.memory.store_interaction.assert_any_call(
            "test query 1", "test response 1"
        )
        mock_memory_aware_agent.memory.store_interaction.assert_any_call(
            "test query 2", "test response 2"
        )
    
    def test_restore_from_session_no_memory(self):
        """Test restoring session when agent has no memory."""
        class NoMemoryAgent(MemoryAwareAgent):
            def __init__(self):
                self.memory = None
            
            def __call__(self, query: str) -> str:
                return f"Response to: {query}"
            
            def create_workflow(self, *args, **kwargs):
                return Mock()
        
        agent = NoMemoryAgent()
        result = agent.restore_from_session([{"user_input": "test", "agent_response": "test"}])
        
        assert result is False
    
    def test_get_session_state(self, mock_memory_aware_agent):
        """Test getting session state from agent."""
        session_state = mock_memory_aware_agent.get_session_state()
        
        assert "memory_state" in session_state
        assert "interactions" in session_state
        assert session_state["memory_state"]["interaction_count"] == 1
    
    def test_get_session_state_no_memory(self):
        """Test getting session state when agent has no memory."""
        class NoMemoryAgent(MemoryAwareAgent):
            def __init__(self):
                self.memory = None
            
            def __call__(self, query: str) -> str:
                return f"Response to: {query}"
            
            def create_workflow(self, *args, **kwargs):
                return Mock()
        
        agent = NoMemoryAgent()
        session_state = agent.get_session_state()
        
        assert session_state == {}


class TestSessionFormatMigration:
    """Test session format migration from old to new versions."""
    
    def test_load_old_format_session(self, session_manager):
        """Test loading and migrating old format sessions."""
        # Create old format session (v0.9)
        old_session = {
            "agent_name": "test_agent",
            "created_at": "2024-01-01T00:00:00",
            "interactions": [{"user_input": "test", "agent_response": "response"}]
        }
        session_manager.session_file.write_text(json.dumps(old_session))
        
        # Load and validate migration
        loaded_session = session_manager._load_and_validate_session()
        
        assert loaded_session["format_version"] == "0.9"
        assert "last_updated" in loaded_session
        assert "memory_state" in loaded_session
        assert loaded_session["memory_state"] == {}
    
    def test_validate_old_format_compatibility(self, session_manager):
        """Test that old format sessions are considered valid."""
        old_session = {
            "agent_name": "test_agent",
            "created_at": "2024-01-01T00:00:00",
            "interactions": []
        }
        session_manager.session_file.write_text(json.dumps(old_session))
        
        assert session_manager._validate_session_format()


@pytest.mark.asyncio
async def test_cli_integration_workflow(temp_session_dir):
    """Test the complete CLI workflow with session management."""
    from agentdk.cli.main import run_agent_interactive
    
    # Mock agent with memory support
    mock_agent = Mock()
    mock_agent.__class__.__name__ = "TestAgent"
    mock_agent.query = Mock(return_value="test response")
    mock_agent.restore_from_session = Mock(return_value=True)
    mock_agent.get_session_state = Mock(return_value={"test": "state"})
    mock_agent.memory = Mock()
    mock_agent.memory.working_memory = Mock()
    mock_agent.memory.working_memory.clear = Mock()
    
    # Mock input/output for testing
    with patch('builtins.input', side_effect=['test query', 'exit']), \
         patch('builtins.print') as mock_print, \
         patch('sys.stdin.isatty', return_value=True), \
         patch('agentdk.agent.session_manager.SessionManager.__init__') as mock_session_init, \
         patch('agentdk.agent.session_manager.SessionManager.start_new_session') as mock_start, \
         patch('agentdk.agent.session_manager.SessionManager.save_interaction') as mock_save, \
         patch('agentdk.agent.session_manager.SessionManager.close') as mock_close:
        
        mock_session_init.return_value = None
        mock_start.return_value = None
        mock_save.return_value = None
        mock_close.return_value = None
        
        # Test fresh session (resume=False)
        await run_agent_interactive(mock_agent, resume=False)
        
        mock_start.assert_called_once()
        mock_agent.query.assert_called_with('test query')
        mock_print.assert_called_with('test response')
        mock_save.assert_called_once()
        mock_close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])