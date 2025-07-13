"""Tests for agentdk.agent.factory module - updated for new architecture."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from agentdk.agent.factory import create_agent
from agentdk.agent.agent_interface import SubAgentWithMCP, SubAgentWithoutMCP
from agentdk.exceptions import AgentInitializationError


class TestCreateAgent:
    """Test the create_agent factory function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
    
    def test_create_mcp_agent_success(self):
        """Test successful MCP agent creation."""
        with patch.object(SubAgentWithMCP, '__init__', return_value=None) as mock_init:
            result = create_agent(
                'mcp',
                llm=self.mock_llm,
                mcp_config_path='test_config.json',
                name='test_agent',
                prompt='Test prompt'
            )
            
            assert isinstance(result, SubAgentWithMCP)
            mock_init.assert_called_once()
            
            # Check that the correct arguments were passed
            call_args = mock_init.call_args
            assert call_args.kwargs['llm'] == self.mock_llm
            assert call_args.kwargs['mcp_config_path'] == 'test_config.json'
            assert call_args.kwargs['name'] == 'test_agent'
            assert call_args.kwargs['prompt'] == 'Test prompt'
    
    def test_create_mcp_agent_missing_config_path(self):
        """Test MCP agent creation fails without config path."""
        with pytest.raises(AgentInitializationError) as exc_info:
            create_agent('mcp', llm=self.mock_llm)
        
        assert "Failed to create mcp agent" in str(exc_info.value)
        assert "mcp_config_path is required for MCP agents" in str(exc_info.value)
    
    def test_create_tools_agent_success(self):
        """Test successful tools agent creation."""
        test_tools = [Mock(), Mock()]
        
        with patch.object(SubAgentWithoutMCP, '__init__', return_value=None) as mock_init:
            result = create_agent(
                'tools',
                llm=self.mock_llm,
                tools=test_tools,
                name='tools_agent',
                prompt='Tools prompt'
            )
            
            assert isinstance(result, SubAgentWithoutMCP)
            mock_init.assert_called_once()
            
            # Check that the correct arguments were passed
            call_args = mock_init.call_args
            assert call_args.kwargs['llm'] == self.mock_llm
            assert call_args.kwargs['tools'] == test_tools
            assert call_args.kwargs['name'] == 'tools_agent'
            assert call_args.kwargs['prompt'] == 'Tools prompt'
    
    def test_create_tools_agent_empty_tools(self):
        """Test tools agent creation with empty tools list."""
        with patch.object(SubAgentWithoutMCP, '__init__', return_value=None) as mock_init:
            result = create_agent('tools', llm=self.mock_llm)
            
            assert isinstance(result, SubAgentWithoutMCP)
            
            # Should default to empty tools list
            call_args = mock_init.call_args
            assert call_args.kwargs['tools'] == []
    
    def test_create_agent_unknown_type(self):
        """Test creation fails with unknown agent type."""
        with pytest.raises(AgentInitializationError) as exc_info:
            create_agent('unknown', llm=self.mock_llm)
        
        assert "Failed to create unknown agent" in str(exc_info.value)
        assert "Unknown agent_type: unknown" in str(exc_info.value)
    
    @patch('agentdk.agent.factory.create_memory_session')
    def test_create_agent_memory_session_injection(self, mock_create_memory):
        """Test that memory session is created and injected."""
        mock_memory_session = Mock()
        mock_create_memory.return_value = mock_memory_session
        
        with patch.object(SubAgentWithoutMCP, '__init__', return_value=None) as mock_init:
            result = create_agent(
                'tools',
                llm=self.mock_llm,
                name='test_agent'
            )
            
            # Verify memory session creation
            mock_create_memory.assert_called_once_with(name='test_agent')
            
            # Verify memory session was injected
            call_args = mock_init.call_args
            assert call_args.kwargs['memory_session'] == mock_memory_session
    
    def test_create_agent_with_provided_memory_session(self):
        """Test that provided memory session is used instead of creating new one."""
        provided_memory_session = Mock()
        
        with patch('agentdk.agent.factory.create_memory_session') as mock_create_memory, \
             patch.object(SubAgentWithoutMCP, '__init__', return_value=None) as mock_init:
            
            result = create_agent(
                'tools',
                llm=self.mock_llm,
                memory_session=provided_memory_session
            )
            
            # Should not create new memory session
            mock_create_memory.assert_not_called()
            
            # Should use provided memory session
            call_args = mock_init.call_args
            assert call_args.kwargs['memory_session'] == provided_memory_session
    
    def test_create_agent_initialization_error_handling(self):
        """Test that initialization errors are properly wrapped."""
        with patch.object(SubAgentWithoutMCP, '__init__', side_effect=Exception("Init failed")):
            with pytest.raises(AgentInitializationError) as exc_info:
                create_agent('tools', llm=self.mock_llm)
            
            assert "Failed to create tools agent" in str(exc_info.value)
            assert exc_info.value.agent_type == 'tools'
            assert exc_info.value.__cause__.args[0] == "Init failed"
    
    def test_create_agent_kwargs_passthrough(self):
        """Test that additional kwargs are passed through."""
        custom_kwargs = {
            'custom_param1': 'value1',
            'custom_param2': 42
        }
        
        with patch.object(SubAgentWithoutMCP, '__init__', return_value=None) as mock_init:
            result = create_agent(
                'tools',
                llm=self.mock_llm,
                **custom_kwargs
            )
            
            # Check that custom kwargs were passed through
            call_args = mock_init.call_args
            assert call_args.kwargs['custom_param1'] == 'value1'
            assert call_args.kwargs['custom_param2'] == 42


class TestFactoryIntegration:
    """Test factory integration with actual components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
    
    def test_factory_creates_working_mcp_agent(self):
        """Test that factory creates a working MCP agent."""
        # This test uses actual classes but mocks their dependencies
        with patch('agentdk.agent.agent_interface.SubAgentWithMCP._resolve_mcp_config_path') as mock_resolve, \
             patch('agentdk.agent.factory.create_memory_session') as mock_memory:
            
            mock_resolve.return_value = Path('test_config.json')
            mock_memory.return_value = None
            
            agent = create_agent(
                'mcp',
                llm=self.mock_llm,
                mcp_config_path='test_config.json'
            )
            
            # Should be actual SubAgentWithMCP instance
            assert isinstance(agent, SubAgentWithMCP)
            assert agent.llm == self.mock_llm
            assert agent._mcp_config_path == Path('test_config.json')
    
    def test_factory_creates_working_tools_agent(self):
        """Test that factory creates a working tools agent."""
        test_tools = [Mock(), Mock()]
        
        with patch('agentdk.agent.factory.create_memory_session') as mock_memory:
            mock_memory.return_value = None
            
            agent = create_agent(
                'tools',
                llm=self.mock_llm,
                tools=test_tools
            )
            
            # Should be actual SubAgentWithoutMCP instance
            assert isinstance(agent, SubAgentWithoutMCP)
            assert agent.llm == self.mock_llm
            assert agent._tools == test_tools


class TestFactoryLogging:
    """Test factory logging behavior."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
    
    @patch('agentdk.agent.factory.get_logger')
    def test_successful_creation_logging(self, mock_get_logger):
        """Test that successful agent creation is logged."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with patch.object(SubAgentWithoutMCP, '__init__', return_value=None):
            agent = create_agent('tools', llm=self.mock_llm)
            
            # Should log success
            mock_logger.info.assert_called_once_with("Created tools agent successfully")
    
    @patch('agentdk.agent.factory.get_logger')
    def test_failed_creation_logging(self, mock_get_logger):
        """Test that failed agent creation is logged through exception."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with patch.object(SubAgentWithoutMCP, '__init__', side_effect=Exception("Init failed")):
            with pytest.raises(AgentInitializationError):
                create_agent('tools', llm=self.mock_llm)
            
            # Logger should be created (for potential error logging)
            mock_get_logger.assert_called_once()


class TestFactoryErrorScenarios:
    """Test various error scenarios in the factory."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
    
    def test_missing_llm_parameter(self):
        """Test behavior when LLM is not provided."""
        # Note: This should fail during agent initialization, not in factory
        with patch.object(SubAgentWithoutMCP, '__init__', side_effect=TypeError("llm is required")):
            with pytest.raises(AgentInitializationError):
                create_agent('tools', llm=None)
    
    def test_invalid_mcp_config_path(self):
        """Test behavior with invalid MCP config path."""
        with patch.object(SubAgentWithMCP, '__init__', side_effect=FileNotFoundError("Config not found")):
            with pytest.raises(AgentInitializationError) as exc_info:
                create_agent('mcp', llm=self.mock_llm, mcp_config_path='nonexistent.json')
            
            assert "Failed to create mcp agent" in str(exc_info.value)
    
    def test_memory_session_creation_failure(self):
        """Test behavior when memory session creation fails."""
        with patch('agentdk.agent.factory.create_memory_session', side_effect=Exception("Memory error")):
            with pytest.raises(AgentInitializationError) as exc_info:
                create_agent('tools', llm=self.mock_llm)
            
            assert "Failed to create tools agent" in str(exc_info.value)