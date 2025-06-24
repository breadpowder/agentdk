"""Tests for agentdk.agent.factory module."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from agentdk.agent.factory import AgentConfig, create_agent, create_eda_agent, _get_agent_class
from agentdk.exceptions import AgentInitializationError


def test_agent_config_initialization():
    """Test AgentConfig class initialization with various parameters."""
    # Test with minimal parameters
    config = AgentConfig()
    assert config.mcp_config_path is None
    assert config.llm is None
    assert config.system_prompt is None
    assert config.log_level == "INFO"
    assert config.extra_config == {}
    
    # Test with all parameters
    llm_mock = Mock()
    config = AgentConfig(
        mcp_config_path="test/path.json",
        llm=llm_mock,
        system_prompt="Test prompt",
        log_level="DEBUG",
        custom_param="value"
    )
    
    assert config.mcp_config_path == Path("test/path.json")
    assert config.llm is llm_mock
    assert config.system_prompt == "Test prompt"
    assert config.log_level == "DEBUG"
    assert config.extra_config["custom_param"] == "value"


def test_create_eda_agent_backward_compatibility():
    """Test create_eda_agent function maintains backward compatibility."""
    llm_mock = Mock()
    prompt = "Test EDA prompt"
    mcp_config = "test_config.json"
    
    with patch('agentdk.agent.factory.create_agent') as mock_create_agent:
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent
        
        result = create_eda_agent(
            llm=llm_mock,
            prompt=prompt,
            mcp_config_path=mcp_config
        )
        
        # Verify create_agent was called with correct parameters
        mock_create_agent.assert_called_once()
        args, kwargs = mock_create_agent.call_args
        
        assert args[0] == 'eda'  # agent_type
        config = kwargs['config']
        assert config.llm is llm_mock
        assert config.system_prompt == prompt
        assert config.mcp_config_path == Path(mcp_config)


def test_get_agent_class_supported_types():
    """Test _get_agent_class returns appropriate classes for supported types."""
    with patch('agentdk.agent.factory._get_eda_agent_class') as mock_eda_class, \
         patch('agentdk.agent.factory._get_custom_agent_class') as mock_custom_class:
        
        # Mock the agent classes
        mock_eda_class.return_value = Mock()
        mock_custom_class.return_value = Mock()
        
        # Test EDA agent type
        eda_class = _get_agent_class('eda')
        assert eda_class is not None
        mock_eda_class.assert_called_once()
        
        # Test custom agent type
        custom_class = _get_agent_class('custom')
        assert custom_class is not None
        mock_custom_class.assert_called_once()


def test_get_agent_class_unsupported_type():
    """Test _get_agent_class raises error for unsupported agent types."""
    with pytest.raises(AgentInitializationError) as exc_info:
        _get_agent_class('unsupported_type')
    
    assert "Unsupported agent type 'unsupported_type'" in str(exc_info.value)
    assert exc_info.value.agent_type == 'unsupported_type'


def test_create_agent_with_config_merging():
    """Test create_agent properly merges configuration from different sources."""
    llm_mock = Mock()
    initial_config = AgentConfig(system_prompt="Initial prompt")
    
    with patch('agentdk.agent.factory._get_agent_class') as mock_get_class, \
         patch('agentdk.agent.factory._instantiate_agent') as mock_instantiate:
        
        # Mock agent class and instance
        mock_class = Mock()
        mock_agent = Mock()
        mock_get_class.return_value = mock_class
        mock_instantiate.return_value = mock_agent
        
        result = create_agent(
            'eda',
            config=initial_config,
            llm=llm_mock,
            custom_param="test_value"
        )
        
        # Verify the configuration was properly merged
        mock_instantiate.assert_called_once()
        config = mock_instantiate.call_args[0][1]  # Second argument (config)
        
        assert config.llm is llm_mock  # LLM should be set from parameter
        assert config.system_prompt == "Initial prompt"  # Should keep original
        assert config.extra_config["custom_param"] == "test_value"  # Should be in extra_config 