"""Tests for agentdk.cli.interactive module."""

import pytest
import asyncio
import signal
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import StringIO

from agentdk.cli.interactive import InteractiveCLI, run_interactive_session


class TestInteractiveCLI:
    """Test the InteractiveCLI class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_agent = Mock()
        self.mock_agent.query = Mock(return_value="Test response")
        self.agent_name = "test_agent"
        self.mock_session_manager = AsyncMock()
        
        # Mock signal.signal to avoid actual signal handling in tests
        self.signal_patcher = patch('signal.signal')
        self.mock_signal = self.signal_patcher.start()
        
    def teardown_method(self):
        """Clean up after tests."""
        self.signal_patcher.stop()
    
    def test_init(self):
        """Test InteractiveCLI initialization."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        assert cli.agent == self.mock_agent
        assert cli.agent_name == self.agent_name
        assert cli.session_manager == self.mock_session_manager
        assert cli._running is True
        
        # Verify signal handlers were set up
        assert self.mock_signal.call_count >= 1
        # Check that SIGINT handler was registered
        signal_calls = [call[0] for call in self.mock_signal.call_args_list]
        assert signal.SIGINT in signal_calls
    
    def test_signal_handler_setup(self):
        """Test signal handler setup with and without SIGTERM."""
        with patch('signal.signal') as mock_signal, \
             patch('hasattr', side_effect=lambda obj, attr: attr == 'SIGTERM'):
            
            cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
            
            # Should register both SIGINT and SIGTERM
            assert mock_signal.call_count == 2
            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGINT in signal_calls
            assert signal.SIGTERM in signal_calls
    
    def test_signal_handler_without_sigterm(self):
        """Test signal handler setup when SIGTERM is not available."""
        with patch('signal.signal') as mock_signal, \
             patch('hasattr', return_value=False):
            
            cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
            
            # Should only register SIGINT
            assert mock_signal.call_count == 1
            mock_signal.assert_called_with(signal.SIGINT, cli._setup_signal_handlers.__locals__['signal_handler'])
    
    @pytest.mark.asyncio
    async def test_invoke_async_with_async_function(self):
        """Test _invoke_async with async function."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        async def async_func(arg):
            return f"async result: {arg}"
        
        result = await cli._invoke_async(async_func, "test")
        assert result == "async result: test"
    
    @pytest.mark.asyncio
    async def test_invoke_async_with_sync_function(self):
        """Test _invoke_async with sync function."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        def sync_func(arg):
            return f"sync result: {arg}"
        
        result = await cli._invoke_async(sync_func, "test")
        assert result == "sync result: test"
    
    @pytest.mark.asyncio
    async def test_process_query_with_query_method(self):
        """Test _process_query with agent that has query method."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        with patch.object(cli, '_invoke_async', return_value="query response") as mock_invoke:
            result = await cli._process_query("test query")
            
            assert result == "query response"
            mock_invoke.assert_called_once_with(self.mock_agent.query, "test query")
    
    @pytest.mark.asyncio
    async def test_process_query_with_callable_agent(self):
        """Test _process_query with callable agent (no query method)."""
        # Create agent without query method but with __call__
        callable_agent = Mock()
        del callable_agent.query  # Remove query method
        callable_agent.__call__ = Mock()
        
        cli = InteractiveCLI(callable_agent, self.agent_name, self.mock_session_manager)
        
        with patch.object(cli, '_invoke_async', return_value="callable response") as mock_invoke:
            result = await cli._process_query("test query")
            
            assert result == "callable response"
            mock_invoke.assert_called_once_with(callable_agent, "test query")
    
    @pytest.mark.asyncio
    async def test_process_query_with_unsupported_agent(self):
        """Test _process_query with agent that has no recognized interface."""
        # Create agent without query method or __call__
        unsupported_agent = Mock()
        del unsupported_agent.query
        del unsupported_agent.__call__
        
        cli = InteractiveCLI(unsupported_agent, self.agent_name, self.mock_session_manager)
        
        result = await cli._process_query("test query")
        
        assert "Error: Agent does not have a recognized interface" in result
    
    @pytest.mark.asyncio
    async def test_process_query_with_exception(self):
        """Test _process_query when agent raises exception."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        with patch.object(cli, '_invoke_async', side_effect=Exception("Agent error")):
            result = await cli._process_query("test query")
            
            assert result == "Error: Agent error"
    
    @patch('click.echo')
    def test_show_help(self, mock_echo):
        """Test _show_help method."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        cli._show_help()
        
        mock_echo.assert_called_once()
        help_text = mock_echo.call_args[0][0]
        assert "Available commands:" in help_text
        assert "help" in help_text
        assert "clear" in help_text
        assert "exit" in help_text
        assert self.agent_name in help_text
    
    @pytest.mark.asyncio
    @patch('click.echo')
    async def test_cleanup(self, mock_echo):
        """Test _cleanup method."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        await cli._cleanup()
        
        mock_echo.assert_called_once()
        message = mock_echo.call_args[0][0]
        assert "Session ended" in message
        assert self.agent_name in message
        self.mock_session_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['exit'])
    @patch('click.echo')
    async def test_run_exit_command(self, mock_echo, mock_input):
        """Test run method with exit command."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        await cli.run()
        
        # Should call cleanup
        self.mock_session_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['quit'])
    @patch('click.echo')
    async def test_run_quit_command(self, mock_echo, mock_input):
        """Test run method with quit command."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        await cli.run()
        
        # Should call cleanup
        self.mock_session_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['q'])
    @patch('click.echo')
    async def test_run_q_command(self, mock_echo, mock_input):
        """Test run method with 'q' command."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        await cli.run()
        
        # Should call cleanup
        self.mock_session_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['help', 'exit'])
    @patch('click.echo')
    async def test_run_help_command(self, mock_echo, mock_input):
        """Test run method with help command."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        with patch.object(cli, '_show_help') as mock_show_help:
            await cli.run()
            
            mock_show_help.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['clear', 'exit'])
    @patch('click.clear')
    @patch('click.echo')
    async def test_run_clear_command(self, mock_echo, mock_clear, mock_input):
        """Test run method with clear command."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        await cli.run()
        
        mock_clear.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['', '  ', 'exit'])
    @patch('click.echo')
    async def test_run_empty_input(self, mock_echo, mock_input):
        """Test run method with empty input."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        with patch.object(cli, '_process_query') as mock_process:
            await cli.run()
            
            # Should not process empty inputs
            mock_process.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['test query', 'exit'])
    @patch('click.echo')
    async def test_run_normal_query(self, mock_echo, mock_input):
        """Test run method with normal user query."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        with patch.object(cli, '_process_query', return_value="agent response") as mock_process:
            await cli.run()
            
            mock_process.assert_called_once_with('test query')
            # Should save interaction
            self.mock_session_manager.save_interaction.assert_called_once_with('test query', 'agent response')
            
            # Should display response
            echo_calls = mock_echo.call_args_list
            response_call = next((call for call in echo_calls if 'agent response' in str(call)), None)
            assert response_call is not None
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['test query', 'exit'])
    @patch('click.echo')
    async def test_run_empty_response(self, mock_echo, mock_input):
        """Test run method when agent returns empty response."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        with patch.object(cli, '_process_query', return_value="") as mock_process:
            await cli.run()
            
            # Should not display empty response
            echo_calls = [str(call) for call in mock_echo.call_args_list]
            assert not any(f"[{self.agent_name}]:" in call for call in echo_calls)
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=[EOFError()])
    @patch('click.echo')
    async def test_run_eof_error(self, mock_echo, mock_input):
        """Test run method with EOFError (Ctrl+D)."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        await cli.run()
        
        # Should call cleanup
        self.mock_session_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=[KeyboardInterrupt()])
    @patch('click.echo')
    async def test_run_keyboard_interrupt(self, mock_echo, mock_input):
        """Test run method with KeyboardInterrupt (Ctrl+C)."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        await cli.run()
        
        # Should call cleanup
        self.mock_session_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=[Exception("Input error"), 'exit'])
    @patch('click.secho')
    @patch('click.echo')
    async def test_run_input_exception(self, mock_echo, mock_secho, mock_input):
        """Test run method with exception during input processing."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        await cli.run()
        
        # Should display error message
        mock_secho.assert_called()
        error_call = mock_secho.call_args
        assert "Error processing query" in error_call[0][0]
        assert error_call[1]['fg'] == "red"


class TestRunInteractiveSession:
    """Test the run_interactive_session function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_agent = Mock()
        self.agent_name = "test_agent"
    
    @pytest.mark.asyncio
    @patch('agentdk.cli.interactive.SessionManager')
    @patch('agentdk.cli.interactive.InteractiveCLI')
    @patch('click.echo')
    async def test_run_interactive_session_new_session(self, mock_echo, mock_cli_class, mock_session_manager_class):
        """Test run_interactive_session with new session."""
        # Set up mocks
        mock_session_manager = AsyncMock()
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_cli = AsyncMock()
        mock_cli_class.return_value = mock_cli
        
        # Run function
        await run_interactive_session(self.mock_agent, self.agent_name, resume_session=False)
        
        # Verify session manager creation
        mock_session_manager_class.assert_called_once_with(self.agent_name)
        
        # Verify new session started
        mock_session_manager.start_new_session.assert_called_once()
        mock_session_manager.load_session.assert_not_called()
        
        # Verify CLI creation and execution
        mock_cli_class.assert_called_once_with(self.mock_agent, self.agent_name, mock_session_manager)
        mock_cli.run.assert_called_once()
        
        # Should not show session loaded message
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert not any("Previous session loaded" in call for call in echo_calls)
    
    @pytest.mark.asyncio
    @patch('agentdk.cli.interactive.SessionManager')
    @patch('agentdk.cli.interactive.InteractiveCLI')
    @patch('click.echo')
    async def test_run_interactive_session_resume_session(self, mock_echo, mock_cli_class, mock_session_manager_class):
        """Test run_interactive_session with session resumption."""
        # Set up mocks
        mock_session_manager = AsyncMock()
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_cli = AsyncMock()
        mock_cli_class.return_value = mock_cli
        
        # Run function with resume
        await run_interactive_session(self.mock_agent, self.agent_name, resume_session=True)
        
        # Verify session resumption
        mock_session_manager.load_session.assert_called_once()
        mock_session_manager.start_new_session.assert_not_called()
        
        # Verify session loaded message
        mock_echo.assert_called_with("Previous session loaded.")
        
        # Verify CLI creation and execution
        mock_cli_class.assert_called_once_with(self.mock_agent, self.agent_name, mock_session_manager)
        mock_cli.run.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('agentdk.cli.interactive.SessionManager')
    @patch('agentdk.cli.interactive.InteractiveCLI')
    async def test_run_interactive_session_default_resume(self, mock_cli_class, mock_session_manager_class):
        """Test run_interactive_session with default resume_session parameter."""
        # Set up mocks
        mock_session_manager = AsyncMock()
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_cli = AsyncMock()
        mock_cli_class.return_value = mock_cli
        
        # Run function without resume parameter (should default to False)
        await run_interactive_session(self.mock_agent, self.agent_name)
        
        # Should start new session by default
        mock_session_manager.start_new_session.assert_called_once()
        mock_session_manager.load_session.assert_not_called()


class TestSignalHandlerIntegration:
    """Test signal handler integration and behavior."""
    
    @patch('sys.exit')
    @patch('click.echo')
    def test_signal_handler_functionality(self, mock_echo, mock_exit):
        """Test signal handler function behavior."""
        mock_agent = Mock()
        mock_session_manager = AsyncMock()
        
        # Create CLI and extract the signal handler
        cli = InteractiveCLI(mock_agent, "test_agent", mock_session_manager)
        
        # Get the signal handler function that was registered
        # We need to access it through the mock calls
        with patch('signal.signal') as mock_signal:
            cli._setup_signal_handlers()
            
            # Get the signal handler function
            sigint_call = next(call for call in mock_signal.call_args_list if call[0][0] == signal.SIGINT)
            signal_handler = sigint_call[0][1]
            
            # Test the signal handler
            signal_handler(signal.SIGINT, None)
            
            # Verify behavior
            mock_echo.assert_called_with("\n\nGracefully shutting down...")
            mock_exit.assert_called_with(0)
            assert cli._running is False


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_agent = Mock()
        self.agent_name = "test_agent"
        self.mock_session_manager = AsyncMock()
    
    @pytest.mark.asyncio
    async def test_agent_with_async_query_method(self):
        """Test agent with async query method."""
        async_agent = Mock()
        async_agent.query = AsyncMock(return_value="async response")
        
        cli = InteractiveCLI(async_agent, self.agent_name, self.mock_session_manager)
        
        result = await cli._process_query("test")
        assert result == "async response"
    
    @pytest.mark.asyncio
    async def test_agent_query_returns_non_string(self):
        """Test when agent query returns non-string response."""
        self.mock_agent.query.return_value = {"result": "complex object"}
        
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        result = await cli._process_query("test")
        assert "{'result': 'complex object'}" in result
    
    @pytest.mark.asyncio
    @patch('builtins.input', side_effect=['EXIT', 'QUIT', 'Q'])  # Test case insensitivity
    @patch('click.echo')
    async def test_case_insensitive_commands(self, mock_echo, mock_input):
        """Test that commands are case insensitive."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        # Test with uppercase EXIT - should exit immediately
        await cli.run()
        
        # Should call cleanup
        self.mock_session_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_manager_save_interaction_error(self):
        """Test behavior when session manager fails to save interaction."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        # Make save_interaction raise an error
        self.mock_session_manager.save_interaction.side_effect = Exception("Save error")
        
        with patch('builtins.input', side_effect=['test query', 'exit']), \
             patch('click.echo'), \
             patch('click.secho') as mock_secho:
            
            await cli.run()
            
            # Should handle the error gracefully
            mock_secho.assert_called()
            error_call = mock_secho.call_args
            assert "Error processing query" in error_call[0][0]
    
    @pytest.mark.asyncio
    async def test_session_manager_close_error(self):
        """Test behavior when session manager fails to close."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        # Make close raise an error
        self.mock_session_manager.close.side_effect = Exception("Close error")
        
        with patch('builtins.input', side_effect=['exit']), \
             patch('click.echo'):
            
            # Should not raise exception even if close fails
            await cli.run()
    
    @pytest.mark.asyncio
    @patch('asyncio.get_event_loop')
    async def test_invoke_async_executor_error(self, mock_get_loop):
        """Test _invoke_async when executor fails."""
        cli = InteractiveCLI(self.mock_agent, self.agent_name, self.mock_session_manager)
        
        mock_loop = Mock()
        mock_loop.run_in_executor = AsyncMock(side_effect=Exception("Executor error"))
        mock_get_loop.return_value = mock_loop
        
        def sync_func():
            return "sync result"
        
        with pytest.raises(Exception, match="Executor error"):
            await cli._invoke_async(sync_func)
    
    def test_agent_name_with_special_characters(self):
        """Test CLI with agent name containing special characters."""
        special_name = "test-agent_123!@#"
        cli = InteractiveCLI(self.mock_agent, special_name, self.mock_session_manager)
        
        assert cli.agent_name == special_name
        
        # Test help display with special characters
        with patch('click.echo') as mock_echo:
            cli._show_help()
            help_text = mock_echo.call_args[0][0]
            assert special_name in help_text