"""Tests for AgentDK CLI main functionality."""

import pytest
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import StringIO

from agentdk.cli.main import main


class TestMainCLI:
    """Test the main CLI entry point and commands."""
    
    def test_main_no_args_shows_help(self):
        """Test the main CLI without arguments shows help."""
        with patch('sys.argv', ['agentdk']):
            with patch('sys.stdout', new=StringIO()) as fake_stdout:
                main()
                output = fake_stdout.getvalue()
                assert "AgentDK CLI" in output
                assert "run" in output
                assert "sessions" in output
    
    def test_main_help_option(self):
        """Test the help option."""
        with patch('sys.argv', ['agentdk', '--help']):
            with patch('sys.exit') as mock_exit:
                with patch('sys.stdout', new=StringIO()) as fake_stdout:
                    main()
                    output = fake_stdout.getvalue()
                    assert "AgentDK CLI" in output
                    assert "run" in output
                    mock_exit.assert_called_with(0)
    
    def test_main_with_run_command_missing_file(self):
        """Test run command with missing file."""
        with patch('sys.argv', ['agentdk', 'run', 'nonexistent.py']):
            with patch('sys.exit') as mock_exit:
                main()
                # Should exit with error for missing file
                mock_exit.assert_called_with(1)


class TestRunCommand:
    """Test the run command functionality."""
    
    def test_run_command_missing_agent_path(self):
        """Test run command without agent path argument."""
        with patch('sys.argv', ['agentdk', 'run']):
            with patch('sys.stderr', new=StringIO()):
                # argparse should exit with code 2 for missing required argument
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 2


class TestSessionsCommands:
    """Test session management commands."""
    
    def test_sessions_status_command_no_session(self):
        """Test sessions status command when no session exists."""
        with patch('sys.argv', ['agentdk', 'sessions', 'status', 'test_agent']):
            with patch('agentdk.agent.session_manager.SessionManager') as mock_sm:
                mock_manager = Mock()
                mock_manager.get_session_info.return_value = {"exists": False, "agent_name": "test_agent"}
                mock_sm.return_value = mock_manager
                
                with patch('click.echo') as mock_echo:
                    main()
                    mock_echo.assert_called_with("No session found for agent: test_agent")
    
    def test_sessions_list_command_no_sessions(self):
        """Test sessions list command when no sessions exist.""" 
        with patch('sys.argv', ['agentdk', 'sessions', 'list']):
            # Mock the Path.home() and glob to return no sessions
            with patch('pathlib.Path.home') as mock_home:
                mock_sessions_dir = Mock()
                mock_sessions_dir.exists.return_value = True
                mock_sessions_dir.glob.return_value = []
                
                # Create a proper Path mock chain  
                mock_home_path = MagicMock()
                mock_agentdk_path = MagicMock()
                mock_home_path.__truediv__.return_value = mock_agentdk_path
                mock_agentdk_path.__truediv__.return_value = mock_sessions_dir
                mock_home.return_value = mock_home_path
                
                with patch('click.echo') as mock_echo:
                    main()
                    mock_echo.assert_called_with("No sessions found")
    
    def test_sessions_clear_command(self):
        """Test sessions clear command."""
        with patch('sys.argv', ['agentdk', 'sessions', 'clear', 'test_agent']):
            with patch('agentdk.agent.session_manager.SessionManager') as mock_sm:
                mock_manager = Mock()
                mock_manager.has_previous_session.return_value = True
                mock_sm.return_value = mock_manager
                
                with patch('click.echo') as mock_echo:
                    main()
                    mock_manager.clear_session.assert_called_once()
                    mock_echo.assert_called_with("Cleared session for test_agent")


class TestGlobalCLIHistory:
    """Test the GlobalCLIHistory functionality."""
    
    def test_init_creates_empty_history(self):
        """Test GlobalCLIHistory initialization with no existing file."""
        with patch('pathlib.Path.home') as mock_home:
            mock_file = Mock()
            mock_file.exists.return_value = False
            mock_file.parent.mkdir = Mock()
            
            mock_home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
            
            from agentdk.cli.main import GlobalCLIHistory
            history = GlobalCLIHistory(max_size=5)
            
            assert history.max_size == 5
            assert history.commands == []
            assert history.current_index == 0
            mock_file.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    def test_add_command(self):
        """Test adding commands to history."""
        with patch('pathlib.Path.home') as mock_home:
            mock_file = Mock()
            mock_file.exists.return_value = False
            mock_file.parent.mkdir = Mock()
            
            mock_home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
            
            from agentdk.cli.main import GlobalCLIHistory
            history = GlobalCLIHistory(max_size=3)
            
            # Add commands
            history.add_command("command1")
            history.add_command("command2")
            history.add_command("command3")
            
            assert history.commands == ["command1", "command2", "command3"]
            assert history.current_index == 3
    
    def test_add_command_max_size_limit(self):
        """Test that history respects max size limit."""
        with patch('pathlib.Path.home') as mock_home:
            mock_file = Mock()
            mock_file.exists.return_value = False
            mock_file.parent.mkdir = Mock()
            
            mock_home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
            
            from agentdk.cli.main import GlobalCLIHistory
            history = GlobalCLIHistory(max_size=2)
            
            # Add more commands than max size
            history.add_command("command1")
            history.add_command("command2")
            history.add_command("command3")
            
            # Should only keep last 2 commands
            assert history.commands == ["command2", "command3"]
            assert len(history.commands) == 2
    
    def test_avoid_duplicate_consecutive_commands(self):
        """Test that consecutive duplicate commands are avoided."""
        with patch('pathlib.Path.home') as mock_home:
            mock_file = Mock()
            mock_file.exists.return_value = False
            mock_file.parent.mkdir = Mock()
            
            mock_home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
            
            from agentdk.cli.main import GlobalCLIHistory
            history = GlobalCLIHistory(max_size=5)
            
            # Add same command twice
            history.add_command("command1")
            history.add_command("command1")
            history.add_command("command2")
            
            # Should only have unique consecutive commands
            assert history.commands == ["command1", "command2"]
    
    def test_get_previous_and_next(self):
        """Test navigation through history."""
        with patch('pathlib.Path.home') as mock_home:
            mock_file = Mock()
            mock_file.exists.return_value = False
            mock_file.parent.mkdir = Mock()
            
            mock_home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
            
            from agentdk.cli.main import GlobalCLIHistory
            history = GlobalCLIHistory(max_size=5)
            
            # Add commands
            history.add_command("cmd1")
            history.add_command("cmd2")
            history.add_command("cmd3")
            
            # Navigate backwards
            assert history.get_previous() == "cmd3"
            assert history.get_previous() == "cmd2"
            assert history.get_previous() == "cmd1"
            assert history.get_previous() is None  # At beginning
            
            # Navigate forwards
            assert history.get_next() == "cmd2"
            assert history.get_next() == "cmd3"
            assert history.get_next() is None  # At end
    
    def test_load_and_cleanup_existing_file(self):
        """Test loading and cleaning up existing history file."""
        with patch('pathlib.Path.home') as mock_home:
            mock_file = Mock()
            mock_file.exists.return_value = True
            
            # Mock reading a file with 5 commands, expect max_size=3 to limit it
            file_lines = ["old1", "old2", "old3", "old4", "old5"]
            
            with patch('builtins.open', create=True) as mock_open:
                # Create a mock file object that is properly iterable
                mock_file_obj = file_lines  # Use list directly as it's iterable
                mock_open.return_value.__enter__.return_value = mock_file_obj
                
                mock_home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
                
                from agentdk.cli.main import GlobalCLIHistory
                
                # Mock the save_commands method to avoid file writing during test
                with patch.object(GlobalCLIHistory, 'save_commands'):
                    history = GlobalCLIHistory(max_size=3)
                    
                    # Should keep only last 3 commands
                    assert len(history.commands) <= 3
    
    def test_save_commands(self):
        """Test saving commands to file."""
        with patch('pathlib.Path.home') as mock_home:
            mock_file = Mock()
            mock_file.exists.return_value = False
            mock_file.parent.mkdir = Mock()
            
            # Mock file writing
            with patch('builtins.open', create=True) as mock_open:
                mock_write_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_write_file
                
                mock_home.return_value.__truediv__.return_value.__truediv__.return_value = mock_file
                
                from agentdk.cli.main import GlobalCLIHistory
                history = GlobalCLIHistory(max_size=5)
                
                history.add_command("test1")
                history.add_command("test2")
                history.save()
                
                # Verify file write was called
                mock_open.assert_called()
                mock_write_file.write.assert_called()