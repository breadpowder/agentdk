"""Unit tests for CLI session management functionality."""

import pytest
import tempfile
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, mock_open

from agentdk.cli.session_manager import SessionManager


class TestSessionManager:
    """Test cases for SessionManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.session_manager = SessionManager("test_agent", self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_start_new_session(self):
        """Test starting a new session."""
        await self.session_manager.start_new_session()
        
        assert self.session_manager.current_session is not None
        assert self.session_manager.current_session["agent_name"] == "test_agent"
        assert "created_at" in self.session_manager.current_session
        assert self.session_manager.current_session["interactions"] == []
    
    @pytest.mark.asyncio
    async def test_save_interaction(self):
        """Test saving an interaction to session."""
        await self.session_manager.start_new_session()
        
        await self.session_manager.save_interaction("Hello", "Hi there!")
        
        interactions = self.session_manager.current_session["interactions"]
        assert len(interactions) == 1
        assert interactions[0]["user_input"] == "Hello"
        assert interactions[0]["agent_response"] == "Hi there!"
        assert "timestamp" in interactions[0]
    
    @pytest.mark.asyncio
    async def test_get_session_context(self):
        """Test getting session context."""
        await self.session_manager.start_new_session()
        await self.session_manager.save_interaction("Hello", "Hi!")
        await self.session_manager.save_interaction("How are you?", "Good!")
        
        context = self.session_manager.get_session_context()
        assert len(context) == 2
        assert context[0]["user_input"] == "Hello"
        assert context[1]["user_input"] == "How are you?"
    
    @pytest.mark.asyncio
    async def test_load_session_file_not_exists(self):
        """Test loading session when file doesn't exist."""
        result = await self.session_manager.load_session()
        
        # Should return False and start new session
        assert result is False
        assert self.session_manager.current_session["agent_name"] == "test_agent"
        assert self.session_manager.current_session["interactions"] == []
    
    @pytest.mark.asyncio
    async def test_load_session_file_exists(self):
        """Test loading session when file exists."""
        # Create a session file
        session_data = {
            "agent_name": "test_agent",
            "created_at": "2024-01-01T00:00:00",
            "interactions": [
                {
                    "timestamp": "2024-01-01T00:01:00",
                    "user_input": "Previous question",
                    "agent_response": "Previous answer"
                }
            ]
        }
        
        session_file = self.temp_dir / "test_agent_session.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f)
        
        with patch('click.echo'):  # Suppress output
            result = await self.session_manager.load_session()
        
        assert result is True
        assert self.session_manager.current_session == session_data
    
    @pytest.mark.asyncio
    async def test_load_session_invalid_json(self):
        """Test loading session with invalid JSON."""
        # Create an invalid session file
        session_file = self.temp_dir / "test_agent_session.json"
        with open(session_file, 'w') as f:
            f.write("invalid json content")
        
        with patch('click.echo'):  # Suppress output
            with patch('click.secho'):  # Suppress error output
                result = await self.session_manager.load_session()
        
        # Should return False and start new session
        assert result is False
        assert self.session_manager.current_session["agent_name"] == "test_agent"
        assert self.session_manager.current_session["interactions"] == []
    
    @pytest.mark.asyncio
    async def test_clear_session(self):
        """Test clearing session."""
        await self.session_manager.start_new_session()
        await self.session_manager.save_interaction("Test", "Response")
        
        # Verify interaction was saved
        assert len(self.session_manager.current_session["interactions"]) == 1
        
        with patch('click.echo'):  # Suppress output
            self.session_manager.clear_session()
        
        # Verify session was cleared
        assert len(self.session_manager.current_session["interactions"]) == 0
        assert self.session_manager.current_session["agent_name"] == "test_agent"
    
    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test closing session."""
        await self.session_manager.start_new_session()
        await self.session_manager.save_interaction("Final question", "Final answer")
        
        with patch('click.echo'):  # Suppress output
            await self.session_manager.close()
        
        # Verify session file was created
        session_file = self.temp_dir / "test_agent_session.json"
        assert session_file.exists()
        
        # Verify content
        with open(session_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["agent_name"] == "test_agent"
        assert len(saved_data["interactions"]) == 1
        assert saved_data["interactions"][0]["user_input"] == "Final question"


class TestSessionManagerIntegration:
    """Integration tests for SessionManager."""
    
    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self):
        """Test complete session lifecycle."""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Create session manager
            sm = SessionManager("integration_test", temp_dir)
            
            # Start new session
            await sm.start_new_session()
            assert len(sm.get_session_context()) == 0
            
            # Add interactions
            await sm.save_interaction("Question 1", "Answer 1")
            await sm.save_interaction("Question 2", "Answer 2")
            
            assert len(sm.get_session_context()) == 2
            
            # Close and save session
            with patch('click.echo'):
                await sm.close()
            
            # Create new session manager and load previous session
            sm2 = SessionManager("integration_test", temp_dir)
            with patch('click.echo'):
                result = await sm2.load_session()
            
            assert result is True
            context = sm2.get_session_context()
            assert len(context) == 2
            assert context[0]["user_input"] == "Question 1"
            assert context[1]["user_input"] == "Question 2"
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)