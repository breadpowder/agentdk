"""Unit tests for AgentDK Builder Pattern.

Tests the AgentBuilder class and Agent factory function to ensure
proper functionality, error handling, and compatibility following
the organized test structure that mirrors src/agentdk/builder/.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for testing
test_dir = Path(__file__).parent.parent.parent
src_dir = test_dir / 'src'
sys.path.insert(0, str(src_dir))

from agentdk import Agent
from agentdk.builder.agent_builder import AgentBuilder
from agentdk.agent.agent_interface import SubAgent


class TestAgentBuilder:
    """Test cases for AgentBuilder class."""

    def test_agent_factory_returns_builder(self):
        """Test that Agent() returns an AgentBuilder instance."""
        builder = Agent()
        assert isinstance(builder, AgentBuilder)

    def test_with_llm_sets_llm(self):
        """Test that with_llm() sets the LLM correctly."""
        mock_llm = Mock()
        builder = Agent().with_llm(mock_llm)
        
        assert builder._config['llm'] is mock_llm
        assert isinstance(builder, AgentBuilder)  # Method chaining

    def test_with_prompt_string(self):
        """Test with_prompt() with string input."""
        prompt = "You are a helpful assistant"
        builder = Agent().with_prompt(prompt)
        
        assert builder._config['prompt'] == prompt

    def test_with_prompt_function(self):
        """Test with_prompt() with function input."""
        def get_prompt():
            return "Function-generated prompt"
        
        builder = Agent().with_prompt(get_prompt)
        assert builder._config['prompt'] is get_prompt

    def test_with_mcp_config(self):
        """Test with_mcp_config() sets MCP configuration path."""
        config_path = "config.json"
        builder = Agent().with_mcp_config(config_path)
        
        assert builder._config['mcp_config_path'] == config_path

    def test_with_tools(self):
        """Test with_tools() sets tools list."""
        tools = [Mock(), Mock()]
        builder = Agent().with_tools(tools)
        
        assert builder._config['tools'] is tools

    def test_with_name(self):
        """Test with_name() sets agent name."""
        name = "test_agent"
        builder = Agent().with_name(name)
        
        assert builder._config['name'] == name

    def test_method_chaining(self, mock_llm, sample_mcp_config):
        """Test that all methods support fluent API chaining using fixtures."""
        tools = [Mock()]
        
        builder = (Agent()
            .with_llm(mock_llm)
            .with_prompt("Test prompt")
            .with_mcp_config("config.json")
            .with_tools(tools)
            .with_name("chained_agent"))
        
        assert builder._config['llm'] is mock_llm
        assert builder._config['prompt'] == "Test prompt"
        assert builder._config['mcp_config_path'] == "config.json"
        assert builder._config['tools'] is tools
        assert builder._config['name'] == "chained_agent"


class TestPromptResolution:
    """Test cases for prompt resolution functionality."""

    def test_resolve_string_prompt(self):
        """Test resolving string prompt."""
        builder = AgentBuilder()
        builder._config['prompt'] = "String prompt"
        
        resolved = builder._resolve_prompt()
        assert resolved == "String prompt"

    def test_resolve_function_prompt(self):
        """Test resolving function prompt."""
        def get_prompt():
            return "Function prompt"
        
        builder = AgentBuilder()
        builder._config['prompt'] = get_prompt
        
        resolved = builder._resolve_prompt()
        assert resolved == "Function prompt"

    def test_resolve_file_prompt(self):
        """Test resolving file-based prompt."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("File-based prompt content")
            temp_path = f.name
        
        try:
            builder = AgentBuilder()
            builder._config['prompt'] = temp_path
            
            resolved = builder._resolve_prompt()
            assert resolved == "File-based prompt content"
        finally:
            Path(temp_path).unlink()

    def test_resolve_path_object_prompt(self):
        """Test resolving Path object prompt."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Path object prompt")
            temp_path = Path(f.name)
        
        try:
            builder = AgentBuilder()
            builder._config['prompt'] = temp_path
            
            resolved = builder._resolve_prompt()
            assert resolved == "Path object prompt"
        finally:
            temp_path.unlink()

    def test_resolve_default_prompt(self):
        """Test default prompt when none provided."""
        builder = AgentBuilder()
        # No prompt set
        
        resolved = builder._resolve_prompt()
        assert resolved == "You are a helpful AI assistant."

    def test_resolve_prompt_function_error(self):
        """Test error handling when prompt function fails."""
        def failing_prompt():
            raise ValueError("Prompt function failed")
        
        builder = AgentBuilder()
        builder._config['prompt'] = failing_prompt
        
        with pytest.raises(ValueError, match="Failed to call prompt function"):
            builder._resolve_prompt()

    def test_resolve_prompt_file_not_found(self):
        """Test error handling when prompt file doesn't exist."""
        builder = AgentBuilder()
        builder._config['prompt'] = "nonexistent_file.txt"
        
        # Should treat as string literal, not file
        resolved = builder._resolve_prompt()
        assert resolved == "nonexistent_file.txt"

    def test_resolve_prompt_file_read_error(self):
        """Test error handling when file exists but can't be read."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # Make file unreadable
            temp_path.chmod(0o000)
            
            builder = AgentBuilder()
            builder._config['prompt'] = temp_path
            
            with pytest.raises(ValueError, match="Failed to read prompt file"):
                builder._resolve_prompt()
        finally:
            temp_path.chmod(0o644)  # Restore permissions
            temp_path.unlink()


class TestAgentBuilding:
    """Test cases for building agents."""

    def test_build_requires_llm(self):
        """Test that build() requires LLM to be set."""
        builder = Agent().with_prompt("Test prompt")
        
        with pytest.raises(ValueError, match="LLM is required"):
            builder.build()

    @patch('agentdk.builder.agent_builder.SubAgent')
    def test_build_creates_generic_agent(self, mock_sub_agent):
        """Test that build() creates a generic agent."""
        mock_llm = Mock()
        
        builder = Agent().with_llm(mock_llm).with_prompt("Test prompt")
        
        # Mock the GenericAgent creation process
        with patch.object(builder, '_create_generic_agent') as mock_create:
            mock_agent = Mock(spec=SubAgent)
            mock_create.return_value = mock_agent
            
            agent = builder.build()
            
            mock_create.assert_called_once()
            assert agent is mock_agent

    def test_build_with_all_options(self):
        """Test building agent with all configuration options."""
        mock_llm = Mock()
        tools = [Mock()]
        
        builder = (Agent()
            .with_llm(mock_llm)
            .with_prompt("Full config prompt")
            .with_mcp_config("config.json")
            .with_tools(tools)
            .with_name("full_config_agent"))
        
        # Mock the actual agent creation to focus on configuration
        with patch.object(builder, '_create_generic_agent') as mock_create:
            mock_agent = Mock(spec=SubAgent)
            mock_create.return_value = mock_agent
            
            agent = builder.build()
            
            # Verify configuration was passed correctly
            call_args = mock_create.call_args
            resolved_prompt = call_args[0][0]
            assert resolved_prompt == "Full config prompt"
            
            config = builder._config
            assert config['llm'] is mock_llm
            assert config['mcp_config_path'] == "config.json"
            assert config['tools'] is tools
            assert config['name'] == "full_config_agent"


class TestGenericAgent:
    """Test cases for the generated GenericAgent."""

    def test_generic_agent_implements_interface(self):
        """Test that GenericAgent properly implements SubAgent."""
        mock_llm = Mock()
        
        # Create a minimal working agent
        with patch('langgraph.prebuilt.create_react_agent') as mock_create_react:
            mock_create_react.return_value = Mock()
            
            agent = (Agent()
                .with_llm(mock_llm)
                .with_prompt("Test prompt")
                .build())
            
            # Verify it's a SubAgent
            assert isinstance(agent, SubAgent)

    def test_generic_agent_get_default_prompt(self):
        """Test that GenericAgent returns the resolved prompt."""
        mock_llm = Mock()
        prompt = "Custom prompt for testing"
        
        with patch('langgraph.prebuilt.create_react_agent') as mock_create_react:
            mock_create_react.return_value = Mock()
            
            agent = (Agent()
                .with_llm(mock_llm)
                .with_prompt(prompt)
                .build())
            
            # Test the resolved prompt is returned
            assert agent._get_default_prompt() == prompt

    def test_generic_agent_process_method(self):
        """Test that GenericAgent process method works correctly."""
        mock_llm = Mock()
        
        with patch('langgraph.prebuilt.create_react_agent') as mock_create_react:
            mock_create_react.return_value = Mock()
            
            agent = (Agent()
                .with_llm(mock_llm)
                .with_prompt("Test prompt")
                .build())
            
            # Mock the query method
            with patch.object(agent, 'query', return_value="Test result") as mock_query:
                state = {'user_input': 'Test query'}
                result = agent.process(state)
                
                mock_query.assert_called_once_with('Test query')
                assert result['agent_output'] == "Test result"


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_eda_agent_creation(self):
        """Test creating a complete EDA agent using builder."""
        mock_llm = Mock()
        
        def get_eda_prompt():
            return "You are an EDA expert."
        
        with patch('langgraph.prebuilt.create_react_agent') as mock_create_react:
            mock_create_react.return_value = Mock()
            
            eda_agent = (Agent()
                .with_llm(mock_llm)
                .with_prompt(get_eda_prompt)
                .with_mcp_config("mcp_config.json")
                .with_name("eda_agent")
                .build())
            
            assert isinstance(eda_agent, SubAgent)
            assert eda_agent._get_default_prompt() == "You are an EDA expert."

    def test_full_research_agent_creation(self):
        """Test creating a complete Research agent using builder."""
        mock_llm = Mock()
        mock_tools = [Mock(), Mock()]
        
        research_prompt = "You are a research expert."
        
        with patch('langgraph.prebuilt.create_react_agent') as mock_create_react:
            mock_create_react.return_value = Mock()
            
            research_agent = (Agent()
                .with_llm(mock_llm)
                .with_prompt(research_prompt)
                .with_tools(mock_tools)
                .with_name("research_expert")
                .build())
            
            assert isinstance(research_agent, SubAgent)
            assert research_agent._get_default_prompt() == research_prompt


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_build_without_llm_raises_error(self):
        """Test that building without LLM raises appropriate error."""
        with pytest.raises(ValueError, match="LLM is required"):
            Agent().with_prompt("Test").build()

    def test_invalid_prompt_function_raises_error(self):
        """Test that invalid prompt function raises appropriate error."""
        def broken_prompt():
            raise RuntimeError("Broken prompt function")
        
        mock_llm = Mock()
        
        with pytest.raises(ValueError, match="Failed to call prompt function"):
            (Agent()
                .with_llm(mock_llm)
                .with_prompt(broken_prompt)
                .build())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])