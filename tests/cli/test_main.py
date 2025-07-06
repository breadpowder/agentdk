"""Tests for agentdk.cli.main module."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from click.testing import CliRunner

from agentdk.cli.main import main, cli_run


class TestMainCLI:
    """Test the main CLI entry point and commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_main_group_basic(self):
        """Test the main CLI group without arguments."""
        result = self.runner.invoke(main, [])
        
        # CLI should show help when no command is provided
        assert result.exit_code == 0
        # The output should contain some indication it's the AgentDK CLI
        assert "AgentDK" in result.output or "Usage:" in result.output
    
    def test_main_version_option(self):
        """Test the version option."""
        result = self.runner.invoke(main, ["--version"])
        
        assert result.exit_code == 0
        assert "0.1.0" in result.output
    
    def test_main_help_option(self):
        """Test the help option."""
        result = self.runner.invoke(main, ["--help"])
        
        assert result.exit_code == 0
        assert "AgentDK CLI tools" in result.output
        assert "run" in result.output
    
    def test_run_command_help(self):
        """Test the help for run command."""
        result = self.runner.invoke(main, ["run", "--help"])
        
        assert result.exit_code == 0
        assert "Run an interactive CLI session" in result.output
        assert "--resume" in result.output
        assert "--llm" in result.output
        assert "AGENT_PATH" in result.output


class TestRunCommand:
    """Test the run command functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_run_command_missing_agent_path(self):
        """Test run command without agent path argument."""
        result = self.runner.invoke(main, ["run"])
        
        assert result.exit_code == 2  # Click error code for missing argument
        assert "Missing argument" in result.output or "Usage:" in result.output
    
    def test_run_command_nonexistent_path(self):
        """Test run command with nonexistent path."""
        result = self.runner.invoke(main, ["run", "/nonexistent/path.py"])
        
        assert result.exit_code == 2  # Click validation error
        assert "does not exist" in result.output or "Invalid value" in result.output
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    def test_run_command_successful_execution(self, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test successful run command execution."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("# Test agent file\n")
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            # Set up mocks
            mock_agent = Mock()
            mock_agent.name = "test_agent"
            
            mock_loader = Mock()
            mock_loader.load_agent.return_value = mock_agent
            mock_agent_loader_class.return_value = mock_loader
            
            # Run the command
            result = self.runner.invoke(main, ["run", temp_path])
            
            # Verify success
            assert result.exit_code == 0
            
            # Verify loading message
            assert f"Loading agent from {temp_path}" in result.output
            assert "Agent 'test_agent' ready" in result.output
            
            # Verify calls
            mock_agent_loader_class.assert_called_once()
            mock_loader.load_agent.assert_called_once()
            
            # Verify agent path and name handling
            agent_path_obj = mock_loader.load_agent.call_args[0][0]
            assert str(agent_path_obj) == temp_path
            
            # Verify interactive session was started
            mock_asyncio_run.assert_called_once()
            mock_run_interactive.assert_called_once()
            
            # Verify session parameters
            session_call = mock_run_interactive.call_args
            assert session_call[1]['agent'] == mock_agent
            assert session_call[1]['agent_name'] == "test_agent"
            assert session_call[1]['resume_session'] is False
            
        finally:
            os.unlink(temp_path)
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    def test_run_command_with_resume_flag(self, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test run command with resume flag."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("# Test agent file\n")
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            # Set up mocks
            mock_agent = Mock()
            mock_agent.name = "test_agent"
            
            mock_loader = Mock()
            mock_loader.load_agent.return_value = mock_agent
            mock_agent_loader_class.return_value = mock_loader
            
            # Run with resume flag
            result = self.runner.invoke(main, ["run", temp_path, "--resume"])
            
            assert result.exit_code == 0
            
            # Verify resume flag was passed
            session_call = mock_run_interactive.call_args
            assert session_call[1]['resume_session'] is True
            
        finally:
            os.unlink(temp_path)
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    def test_run_command_with_llm_option(self, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test run command with LLM provider option."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("# Test agent file\n")
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            # Set up mocks
            mock_agent = Mock()
            mock_agent.name = "test_agent"
            
            mock_loader = Mock()
            mock_loader.load_agent.return_value = mock_agent
            mock_agent_loader_class.return_value = mock_loader
            
            # Run with LLM option
            result = self.runner.invoke(main, ["run", temp_path, "--llm", "anthropic"])
            
            assert result.exit_code == 0
            
            # Verify LLM provider was passed to loader
            loader_call = mock_loader.load_agent.call_args
            assert loader_call[1]['llm_provider'] == "anthropic"
            
        finally:
            os.unlink(temp_path)
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    def test_run_command_agent_without_name(self, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test run command with agent that has no name attribute."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("# Test agent file\n")
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            # Set up mocks - agent without name
            mock_agent = Mock()
            del mock_agent.name  # Remove name attribute
            
            mock_loader = Mock()
            mock_loader.load_agent.return_value = mock_agent
            mock_agent_loader_class.return_value = mock_loader
            
            # Run the command
            result = self.runner.invoke(main, ["run", temp_path])
            
            assert result.exit_code == 0
            
            # Should use file stem as agent name
            expected_name = Path(temp_path).stem
            session_call = mock_run_interactive.call_args
            assert session_call[1]['agent_name'] == expected_name
            
        finally:
            os.unlink(temp_path)
    
    @patch('agentdk.cli.main.AgentLoader')
    def test_run_command_loader_error(self, mock_agent_loader_class):
        """Test run command when agent loader raises an error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("# Test agent file\n")
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            # Set up mock to raise error
            mock_loader = Mock()
            mock_loader.load_agent.side_effect = Exception("Failed to load agent")
            mock_agent_loader_class.return_value = mock_loader
            
            # Run the command
            result = self.runner.invoke(main, ["run", temp_path])
            
            # Should exit with error
            assert result.exit_code == 1
            assert "Error: Failed to load agent" in result.output
            
        finally:
            os.unlink(temp_path)
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    def test_run_command_interactive_session_error(self, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test run command when interactive session raises an error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("# Test agent file\n")
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            # Set up mocks
            mock_agent = Mock()
            mock_agent.name = "test_agent"
            
            mock_loader = Mock()
            mock_loader.load_agent.return_value = mock_agent
            mock_agent_loader_class.return_value = mock_loader
            
            # Make asyncio.run raise an error
            mock_asyncio_run.side_effect = Exception("Interactive session failed")
            
            # Run the command
            result = self.runner.invoke(main, ["run", temp_path])
            
            # Should exit with error
            assert result.exit_code == 1
            assert "Error: Interactive session failed" in result.output
            
        finally:
            os.unlink(temp_path)
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    def test_run_command_all_options(self, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test run command with all options."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("# Test agent file\n")
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            # Set up mocks
            mock_agent = Mock()
            mock_agent.name = "test_agent"
            
            mock_loader = Mock()
            mock_loader.load_agent.return_value = mock_agent
            mock_agent_loader_class.return_value = mock_loader
            
            # Run with all options
            result = self.runner.invoke(main, [
                "run", temp_path, 
                "--resume", 
                "--llm", "openai"
            ])
            
            assert result.exit_code == 0
            
            # Verify all parameters
            loader_call = mock_loader.load_agent.call_args
            assert loader_call[1]['llm_provider'] == "openai"
            
            session_call = mock_run_interactive.call_args
            assert session_call[1]['agent'] == mock_agent
            assert session_call[1]['agent_name'] == "test_agent"
            assert session_call[1]['resume_session'] is True
            
        finally:
            os.unlink(temp_path)
    
    def test_run_command_directory_path(self):
        """Test run command with directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a Python file in the directory
            agent_file = Path(temp_dir) / "agent.py"
            agent_file.write_text("# Test agent file\n")
            
            with patch('agentdk.cli.main.AgentLoader') as mock_agent_loader_class, \
                 patch('agentdk.cli.main.run_interactive_session') as mock_run_interactive, \
                 patch('agentdk.cli.main.asyncio.run') as mock_asyncio_run:
                
                # Set up mocks
                mock_agent = Mock()
                mock_agent.name = "test_agent"
                
                mock_loader = Mock()
                mock_loader.load_agent.return_value = mock_agent
                mock_agent_loader_class.return_value = mock_loader
                
                # Run with directory path
                result = self.runner.invoke(main, ["run", temp_dir])
                
                assert result.exit_code == 0
                
                # Verify directory path was passed
                loader_call = mock_loader.load_agent.call_args
                assert str(loader_call[0][0]) == temp_dir


class TestCliRunFunction:
    """Test the cli_run function directly."""
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    @patch('agentdk.cli.main.click.echo')
    @patch('agentdk.cli.main.Path')
    def test_cli_run_function_direct(self, mock_path_class, mock_echo, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test cli_run function called directly."""
        # Set up mocks
        mock_path_obj = Mock()
        mock_path_obj.stem = "test_agent"
        mock_path_class.return_value = mock_path_obj
        
        mock_agent = Mock()
        mock_agent.name = "custom_agent"
        
        mock_loader = Mock()
        mock_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_loader
        
        # Call function directly
        cli_run(agent_path="/test/path.py", resume=True, llm="anthropic")
        
        # Verify calls
        mock_path_class.assert_called_once_with("/test/path.py")
        mock_agent_loader_class.assert_called_once()
        mock_loader.load_agent.assert_called_once_with(mock_path_obj, llm_provider="anthropic")
        
        # Verify echo calls
        assert mock_echo.call_count >= 1
        
        # Verify interactive session
        mock_asyncio_run.assert_called_once()
        session_call = mock_run_interactive.call_args
        assert session_call[1]['agent'] == mock_agent
        assert session_call[1]['agent_name'] == "custom_agent"
        assert session_call[1]['resume_session'] is True
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.click.secho')
    @patch('agentdk.cli.main.sys.exit')
    def test_cli_run_function_exception_handling(self, mock_sys_exit, mock_secho, mock_agent_loader_class):
        """Test cli_run function exception handling."""
        # Set up mock to raise error
        mock_loader = Mock()
        mock_loader.load_agent.side_effect = Exception("Test error")
        mock_agent_loader_class.return_value = mock_loader
        
        # Call function - should not raise, but should call sys.exit
        cli_run(agent_path="/test/path.py", resume=False, llm=None)
        
        # Verify error handling
        mock_secho.assert_called_once_with("Error: Test error", fg="red", err=True)
        mock_sys_exit.assert_called_once_with(1)
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    @patch('agentdk.cli.main.Path')
    def test_cli_run_function_agent_name_fallback(self, mock_path_class, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test cli_run function uses path stem when agent has no name."""
        # Set up mocks
        mock_path_obj = Mock()
        mock_path_obj.stem = "fallback_name"
        mock_path_class.return_value = mock_path_obj
        
        mock_agent = Mock()
        # Remove name attribute to simulate agent without name
        mock_agent.name = None
        
        mock_loader = Mock()
        mock_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_loader
        
        # Call function
        cli_run(agent_path="/test/path.py", resume=False, llm=None)
        
        # Verify fallback name was used
        session_call = mock_run_interactive.call_args
        assert session_call[1]['agent_name'] == "fallback_name"
    
    @patch('agentdk.cli.main.AgentLoader')
    @patch('agentdk.cli.main.run_interactive_session')
    @patch('agentdk.cli.main.asyncio.run')
    @patch('agentdk.cli.main.Path')
    def test_cli_run_function_no_llm_provider(self, mock_path_class, mock_asyncio_run, mock_run_interactive, mock_agent_loader_class):
        """Test cli_run function with no LLM provider specified."""
        # Set up mocks
        mock_path_obj = Mock()
        mock_path_obj.stem = "test_agent"
        mock_path_class.return_value = mock_path_obj
        
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        
        mock_loader = Mock()
        mock_loader.load_agent.return_value = mock_agent
        mock_agent_loader_class.return_value = mock_loader
        
        # Call function with no LLM
        cli_run(agent_path="/test/path.py", resume=False, llm=None)
        
        # Verify load_agent was called with None for llm_provider
        loader_call = mock_loader.load_agent.call_args
        assert loader_call[1]['llm_provider'] is None


class TestMainModuleExecution:
    """Test main module execution patterns."""
    
    def test_main_module_entry_point(self):
        """Test that main() is callable and has expected structure."""
        # Import and verify the main function exists and is callable
        from agentdk.cli.main import main
        assert callable(main)
        
        # The main function should be a Click group
        assert hasattr(main, 'commands')
        assert 'run' in main.commands


class TestClickIntegration:
    """Test Click framework integration and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_context_settings(self):
        """Test that context settings are properly configured."""
        # Import main to check configuration
        from agentdk.cli.main import main
        
        # Check that context settings include max_content_width
        assert hasattr(main, 'context_settings')
        assert main.context_settings.get('max_content_width') == 240
    
    def test_version_option_format(self):
        """Test version option output format."""
        result = self.runner.invoke(main, ["--version"])
        
        assert result.exit_code == 0
        # Should contain version number in standard format
        assert "version 0.1.0" in result.output.lower() or "0.1.0" in result.output
    
    def test_run_command_argument_validation(self):
        """Test that agent_path argument validation works."""
        # Test with invalid path types
        result = self.runner.invoke(main, ["run", ""])
        assert result.exit_code != 0
        
        # Test with valid path format but nonexistent file
        result = self.runner.invoke(main, ["run", "/definitely/does/not/exist.py"])
        assert result.exit_code != 0
    
    def test_run_command_option_types(self):
        """Test that command options have correct types."""
        # Test boolean flag
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("# Test agent file\n")
            temp_file.flush()
            temp_path = temp_file.name
        
        try:
            with patch('agentdk.cli.main.AgentLoader'), \
                 patch('agentdk.cli.main.run_interactive_session'), \
                 patch('agentdk.cli.main.asyncio.run'):
                
                # Test that --resume is boolean
                result = self.runner.invoke(main, ["run", temp_path, "--resume"])
                assert result.exit_code == 0
                
                # Test that --llm accepts string
                result = self.runner.invoke(main, ["run", temp_path, "--llm", "test_provider"])
                assert result.exit_code == 0
                
        finally:
            os.unlink(temp_path)