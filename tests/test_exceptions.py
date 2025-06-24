"""Tests for agentdk.exceptions module."""

import pytest
from agentdk.exceptions import AgentDKError, MCPConfigError, AgentInitializationError


def test_agentdk_error_basic_creation():
    """Test basic AgentDKError creation and message handling."""
    message = "Test error message"
    error = AgentDKError(message)
    
    assert str(error) == message
    assert error.message == message
    assert error.details == {}


def test_agentdk_error_with_details():
    """Test AgentDKError creation with details dictionary."""
    message = "Test error with details"
    details = {"key": "value", "code": 123}
    error = AgentDKError(message, details)
    
    assert error.message == message
    assert error.details == details
    assert error.details["key"] == "value"


def test_mcp_config_error_creation():
    """Test MCPConfigError creation with config path."""
    message = "Invalid MCP configuration"
    config_path = "/path/to/config.json"
    error = MCPConfigError(message, config_path)
    
    assert str(error) == message
    assert error.config_path == config_path
    assert error.details["config_path"] == config_path
    assert isinstance(error, AgentDKError)


def test_agent_initialization_error_creation():
    """Test AgentInitializationError creation with agent type."""
    message = "Failed to initialize agent"
    agent_type = "eda"
    error = AgentInitializationError(message, agent_type)
    
    assert str(error) == message
    assert error.agent_type == agent_type
    assert error.details["agent_type"] == agent_type
    assert isinstance(error, AgentDKError)


def test_exception_inheritance_chain():
    """Test that all custom exceptions inherit from AgentDKError properly."""
    # Test inheritance
    assert issubclass(MCPConfigError, AgentDKError)
    assert issubclass(AgentInitializationError, AgentDKError)
    assert issubclass(AgentDKError, Exception)
    
    # Test that custom exceptions can be caught as AgentDKError
    with pytest.raises(AgentDKError):
        raise MCPConfigError("Test error")
    
    with pytest.raises(AgentDKError):
        raise AgentInitializationError("Test error") 