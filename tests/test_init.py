"""Tests for agentdk.__init__ module."""

import pytest
from unittest.mock import patch
import agentdk
from agentdk import (
    AgentInterface, SubAgentInterface, create_agent, create_eda_agent,
    AgentConfig, AgentDKError, MCPConfigError, AgentInitializationError,
    quick_start
)


def test_package_version():
    """Test that package version is properly defined."""
    assert hasattr(agentdk, '__version__')
    assert isinstance(agentdk.__version__, str)
    assert agentdk.__version__ == "0.1.0"


def test_public_api_exports():
    """Test that all expected public API components are exported."""
    # Test core interfaces
    assert hasattr(agentdk, 'AgentInterface')
    assert hasattr(agentdk, 'SubAgentInterface')
    
    # Test agent creation functions
    assert hasattr(agentdk, 'create_agent')
    assert hasattr(agentdk, 'create_eda_agent')
    assert hasattr(agentdk, 'AgentConfig')
    
    # Test exceptions
    assert hasattr(agentdk, 'AgentDKError')
    assert hasattr(agentdk, 'MCPConfigError')
    assert hasattr(agentdk, 'AgentInitializationError')
    
    # Test utilities
    assert hasattr(agentdk, 'quick_start')


def test_all_exports_list():
    """Test that __all__ contains all expected exports."""
    expected_exports = {
        'AgentInterface', 'SubAgentInterface', 'create_agent', 'create_eda_agent',
        'AgentConfig', 'AgentDKError', 'MCPConfigError', 'AgentInitializationError',
        'quick_start'
    }
    
    assert hasattr(agentdk, '__all__')
    assert set(agentdk.__all__) == expected_exports


def test_quick_start_function():
    """Test that quick_start function works and produces output."""
    with patch('builtins.print') as mock_print:
        quick_start()
        
        # Verify print was called
        mock_print.assert_called()
        
        # Get the printed content
        printed_content = mock_print.call_args[0][0]
        
        # Verify key information is in the output
        assert "AgentDK Quick Start Guide" in printed_content
        assert "Installation:" in printed_content
        assert "Basic Usage:" in printed_content
        assert "create_agent" in printed_content
        assert "create_eda_agent" in printed_content


def test_imports_work_correctly():
    """Test that all imports work correctly without errors."""
    # Test that we can import all main components without issues
    try:
        from agentdk import (
            AgentInterface, SubAgentInterface, create_agent, create_eda_agent,
            AgentConfig, AgentDKError, MCPConfigError, AgentInitializationError
        )
        
        # Test that they are callable/classes as expected
        assert callable(create_agent)
        assert callable(create_eda_agent)
        assert isinstance(AgentConfig, type)
        assert isinstance(AgentDKError, type)
        assert isinstance(MCPConfigError, type)
        assert isinstance(AgentInitializationError, type)
        
    except ImportError as e:
        pytest.fail(f"Import failed: {e}") 