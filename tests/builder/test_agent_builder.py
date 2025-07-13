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

from agentdk import AgentBuilder
from agentdk.builder.agent_builder import AgentBuilder
from agentdk.agent.agent_interface import SubAgent


class TestAgentBuilder:
    """Test cases for AgentBuilder class."""

    def test_agent_factory_returns_builder(self):
        """Test that Agent() returns an AgentBuilder instance."""
        builder = AgentBuilder()
        assert isinstance(builder, AgentBuilder)

    def test_with_llm_sets_llm(self):
        """Test that with_llm() stores the LLM."""
        mock_llm = Mock()
        builder = AgentBuilder().with_llm(mock_llm)
        
        assert builder._config['llm'] is mock_llm

    def test_with_prompt_string(self):
        """Test that with_prompt() stores string prompts."""
        prompt = "You are a helpful assistant."
        builder = AgentBuilder().with_prompt(prompt)
        
        assert builder._config['prompt'] == prompt

    def test_with_prompt_function(self):
        """Test that with_prompt() stores function prompts."""
        def get_prompt():
            return "Dynamic prompt"
        
        builder = AgentBuilder().with_prompt(get_prompt)
        assert builder._config['prompt'] is get_prompt

    def test_with_mcp_config(self):
        """Test that with_mcp_config() stores MCP config path."""
        config_path = "config.json"
        builder = AgentBuilder().with_mcp_config(config_path)
        
        assert builder._config['mcp_config_path'] == config_path

    def test_with_tools(self):
        """Test that with_tools() stores tools list."""
        tools = [Mock(), Mock()]
        builder = AgentBuilder().with_tools(tools)
        
        assert builder._config['tools'] is tools

    def test_with_name(self):
        """Test that with_name() stores agent name."""
        name = "test_agent"
        builder = AgentBuilder().with_name(name)
        
        assert builder._config['name'] == name

    def test_method_chaining(self):
        """Test that all methods support chaining."""
        mock_llm = Mock()
        tools = [Mock()]
        
        builder = (AgentBuilder()
            .with_llm(mock_llm)
            .with_prompt("Chained prompt")
            .with_tools(tools)
            .with_name("chained_agent"))
        
        assert builder._config['llm'] is mock_llm
        assert builder._config['prompt'] == "Chained prompt"
        assert builder._config['tools'] is tools
        assert builder._config['name'] == "chained_agent"


class TestPromptResolution:
    """Test prompt resolution functionality."""

    def test_resolve_string_prompt(self):
        """Test resolving string literal prompts."""
        builder = AgentBuilder()
        builder._config['prompt'] = "String prompt"
        
        resolved = builder._resolve_prompt()
        assert resolved == "String prompt"

    def test_resolve_function_prompt(self):
        """Test resolving function prompts."""
        def get_prompt():
            return "Function prompt"
        
        builder = AgentBuilder()
        builder._config['prompt'] = get_prompt
        
        resolved = builder._resolve_prompt()
        assert resolved == "Function prompt"

    def test_resolve_file_prompt(self):
        """Test resolving file prompts."""
        # Create a temporary file with prompt content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("File prompt content")
            temp_path = Path(f.name)
        
        try:
            builder = AgentBuilder()
            builder._config['prompt'] = temp_path
            
            resolved = builder._resolve_prompt()
            assert resolved == "File prompt content"
        finally:
            temp_path.unlink()

    def test_resolve_path_object_prompt(self):
        """Test resolving Path object prompts."""
        # Create a temporary file with prompt content
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

    def test_resolve_prompt_file_not_found(self):
        """Test that non-existent files are treated as string literals."""
        builder = AgentBuilder()
        builder._config['prompt'] = "nonexistent_file.txt"
        
        # Should treat as string literal, not file
        resolved = builder._resolve_prompt()
        assert resolved == "nonexistent_file.txt"


class TestAgentBuilding:
    """Test agent building functionality."""

    def test_build_requires_llm(self):
        """Test that build() requires an LLM."""
        builder = AgentBuilder()
        
        with pytest.raises(ValueError, match="LLM is required"):
            builder.build()

    def test_build_creates_agent_with_mcp(self):
        """Test that build() creates agent with MCP when config provided."""
        mock_llm = Mock()
        
        with patch('agentdk.builder.agent_builder.SubAgentWithMCP') as MockSubAgentWithMCP:
            mock_agent = Mock(spec=SubAgent)
            MockSubAgentWithMCP.return_value = mock_agent
            
            builder = (AgentBuilder()
                .with_llm(mock_llm)
                .with_prompt("Test prompt")
                .with_mcp_config("config.json"))
            
            agent = builder.build()
            
            MockSubAgentWithMCP.assert_called_once()
            call_kwargs = MockSubAgentWithMCP.call_args[1]
            assert call_kwargs['llm'] is mock_llm
            assert call_kwargs['prompt'] == "Test prompt"
            assert call_kwargs['mcp_config_path'] == "config.json"

    def test_build_creates_agent_without_mcp(self):
        """Test that build() creates agent without MCP when no config provided."""
        mock_llm = Mock()
        
        with patch('agentdk.builder.agent_builder.SubAgentWithoutMCP') as MockSubAgentWithoutMCP:
            mock_agent = Mock(spec=SubAgent)
            MockSubAgentWithoutMCP.return_value = mock_agent
            
            builder = (AgentBuilder()
                .with_llm(mock_llm)
                .with_prompt("Test prompt"))
            
            agent = builder.build()
            
            MockSubAgentWithoutMCP.assert_called_once()
            call_kwargs = MockSubAgentWithoutMCP.call_args[1]
            assert call_kwargs['llm'] is mock_llm
            assert call_kwargs['prompt'] == "Test prompt"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_build_without_llm_raises_error(self):
        """Test that building without LLM raises appropriate error."""
        builder = AgentBuilder().with_prompt("Test prompt")
        
        with pytest.raises(ValueError, match="LLM is required"):
            builder.build()