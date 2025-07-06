"""Tests for agentdk.agent.agent_interface module."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from pathlib import Path
from typing import Dict, Any

from agentdk.agent.agent_interface import AgentInterface, SubAgentInterface
from agentdk.exceptions import AgentInitializationError, MCPConfigError


class ConcreteAgentInterface(AgentInterface):
    """Concrete implementation of AgentInterface for testing."""
    
    def query(self, user_prompt: str, **kwargs) -> str:
        return f"Response to: {user_prompt}"


class ConcreteSubAgentInterface(SubAgentInterface):
    """Concrete implementation of SubAgentInterface for testing."""
    
    def _get_default_prompt(self) -> str:
        return "You are a test agent."
    
    async def _create_langgraph_agent(self) -> None:
        """Create a mock LangGraph agent."""
        self.agent = AsyncMock()
        self.agent.ainvoke = AsyncMock(return_value={
            "messages": [Mock(content="Test response")]
        })
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"processed": True, **state}


class TestAgentInterface:
    """Test the AgentInterface abstract base class."""
    
    def test_init_with_no_config(self):
        """Test initialization with no configuration."""
        agent = ConcreteAgentInterface()
        assert agent.config == {}
    
    def test_init_with_config(self):
        """Test initialization with configuration."""
        config = {"param1": "value1", "param2": "value2"}
        agent = ConcreteAgentInterface(config=config)
        assert agent.config == config
    
    def test_query_method_implementation(self):
        """Test that concrete implementation works."""
        agent = ConcreteAgentInterface()
        result = agent.query("test prompt")
        assert result == "Response to: test prompt"


class TestSubAgentInterface:
    """Test the SubAgentInterface class."""
    
    def test_init_minimal_config(self):
        """Test initialization with minimal configuration."""
        agent = ConcreteSubAgentInterface()
        
        # Check default values
        assert agent.config.get("system_prompt") == "You are a test agent."
        assert agent.llm is None
        assert agent.agent is None
        assert agent.name is None
        assert agent._mcp_config_path is None
        assert agent._tools == []
        assert not agent._initialized
        assert not agent._mcp_config_loaded
        assert agent.logger is not None
    
    def test_init_with_llm(self, mock_llm):
        """Test initialization with LLM."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        assert agent.llm == mock_llm
        assert agent.config["llm"] == mock_llm
    
    def test_init_with_prompt(self):
        """Test initialization with custom prompt."""
        custom_prompt = "You are a specialized test agent."
        agent = ConcreteSubAgentInterface(prompt=custom_prompt)
        
        assert agent.config["system_prompt"] == custom_prompt
    
    def test_init_with_mcp_config_path(self):
        """Test initialization with MCP config path."""
        config_path = "/path/to/config.json"
        agent = ConcreteSubAgentInterface(mcp_config_path=config_path)
        
        assert agent._mcp_config_path == Path(config_path)
    
    def test_init_with_name(self):
        """Test initialization with agent name."""
        agent = ConcreteSubAgentInterface(name="test_agent")
        assert agent.name == "test_agent"
    
    def test_init_with_tools(self):
        """Test initialization with tools."""
        tools = [Mock(), Mock()]
        agent = ConcreteSubAgentInterface(tools=tools)
        assert agent._tools == tools
    
    def test_init_config_merging(self, mock_llm):
        """Test that configuration is properly merged from different sources."""
        initial_config = {"existing_param": "existing_value"}
        prompt = "Custom prompt"
        
        agent = ConcreteSubAgentInterface(
            config=initial_config,
            llm=mock_llm,
            prompt=prompt,
            name="test_agent"
        )
        
        assert agent.config["existing_param"] == "existing_value"
        assert agent.config["llm"] == mock_llm
        assert agent.config["system_prompt"] == prompt
        assert agent.name == "test_agent"
    
    def test_tools_property(self):
        """Test tools property."""
        tools = [Mock(), Mock()]
        agent = ConcreteSubAgentInterface(tools=tools)
        assert agent.tools == tools
    
    def test_is_initialized_property(self):
        """Test is_initialized property."""
        agent = ConcreteSubAgentInterface()
        assert not agent.is_initialized
        
        agent._initialized = True
        assert agent.is_initialized
    
    def test_query_sync_wrapper(self, mock_llm):
        """Test that query method properly wraps async functionality."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        with patch.object(agent, 'query_async', new_callable=AsyncMock) as mock_query_async:
            mock_query_async.return_value = "Test response"
            
            result = agent.query("test prompt")
            
            assert result == "Test response"
            mock_query_async.assert_called_once_with("test prompt")
    
    def test_query_error_handling(self, mock_llm):
        """Test query error handling."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        with patch.object(agent, 'query_async', new_callable=AsyncMock) as mock_query_async:
            mock_query_async.side_effect = Exception("Test error")
            
            result = agent.query("test prompt")
            
            assert "Query execution failed: Test error" in result

    @pytest.mark.asyncio
    async def test_query_async_uninitialized_agent(self, mock_llm):
        """Test query_async initializes agent if not initialized."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        with patch.object(agent, '_initialize', new_callable=AsyncMock) as mock_init:
            result = await agent.query_async("test prompt")
            
            mock_init.assert_called_once()
            # Should return fallback response since no agent created in this test
            assert "Analysis (without tools)" in result

    @pytest.mark.asyncio
    async def test_query_async_with_langgraph_agent(self, mock_llm):
        """Test query_async with LangGraph agent."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        agent._initialized = True
        agent.agent = AsyncMock()
        agent.agent.ainvoke = AsyncMock(return_value={
            "messages": [Mock(content="LangGraph response")]
        })
        
        result = await agent.query_async("test prompt")
        
        assert result == "LangGraph response"
        agent.agent.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_async_without_agent(self, mock_llm):
        """Test query_async fallback when no agent available."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        agent._initialized = True
        agent.agent = None
        
        result = await agent.query_async("test prompt")
        
        assert "CONCRETESUBAGENTINTERFACE Analysis (without tools)" in result
        assert "test prompt" in result

    @pytest.mark.asyncio
    async def test_query_async_with_memory_context(self, mock_llm):
        """Test query_async with memory context parsing."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        agent._initialized = True
        agent.agent = AsyncMock()
        agent.agent.ainvoke = AsyncMock(return_value={
            "messages": [Mock(content="Response with memory")]
        })
        
        memory_prompt = "User query: test question\nMemory context: previous conversation"
        result = await agent.query_async(memory_prompt)
        
        # Verify the prompt was parsed and memory context included
        call_args = agent.agent.ainvoke.call_args[0][0]
        assert "test question" in call_args["messages"][0]
        assert "previous conversation" in call_args["messages"][0]

    @pytest.mark.asyncio
    async def test_query_async_initialization_error_propagation(self, mock_llm):
        """Test that AgentInitializationError is properly propagated."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        with patch.object(agent, '_initialize', new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = AgentInitializationError("Test init error")
            
            with pytest.raises(AgentInitializationError):
                await agent.query_async("test prompt")

    @pytest.mark.asyncio
    async def test_query_async_general_error_handling(self, mock_llm):
        """Test general error handling in query_async."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        agent._initialized = True
        agent.agent = AsyncMock()
        agent.agent.ainvoke = AsyncMock(side_effect=Exception("LangGraph error"))
        
        result = await agent.query_async("test prompt")
        
        assert "Error processing query: LangGraph error" in result

    def test_parse_memory_context_with_context(self):
        """Test parsing memory context from formatted prompt."""
        agent = ConcreteSubAgentInterface()
        
        prompt = "User query: What is the weather?\nMemory context: User lives in San Francisco"
        actual_query, memory_context = agent._parse_memory_context(prompt)
        
        assert actual_query == "What is the weather?"
        assert memory_context == "User lives in San Francisco"

    def test_parse_memory_context_without_context(self):
        """Test parsing when no memory context is present."""
        agent = ConcreteSubAgentInterface()
        
        prompt = "What is the weather?"
        actual_query, memory_context = agent._parse_memory_context(prompt)
        
        assert actual_query == "What is the weather?"
        assert memory_context == ""

    def test_parse_memory_context_malformed(self):
        """Test parsing with malformed memory context."""
        agent = ConcreteSubAgentInterface()
        
        prompt = "Memory context: incomplete format"
        actual_query, memory_context = agent._parse_memory_context(prompt)
        
        assert actual_query == "Memory context: incomplete format"
        assert memory_context == ""

    def test_invoke_method_empty_messages(self):
        """Test invoke method with empty messages."""
        agent = ConcreteSubAgentInterface()
        
        with patch('langchain_core.messages.AIMessage') as MockAIMessage:
            mock_message = Mock()
            MockAIMessage.return_value = mock_message
            
            result = agent.invoke({"messages": []})
            
            assert result == {"messages": [mock_message]}
            MockAIMessage.assert_called_once_with(content="No input provided")

    def test_invoke_method_with_user_message(self, mock_llm):
        """Test invoke method with user message."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        user_message = Mock()
        user_message.type = "human"
        user_message.content = "test question"
        
        with patch.object(agent, 'query', return_value="test response") as mock_query, \
             patch('langchain_core.messages.AIMessage') as MockAIMessage:
            
            mock_ai_message = Mock()
            MockAIMessage.return_value = mock_ai_message
            
            result = agent.invoke({"messages": [user_message]})
            
            mock_query.assert_called_once_with("test question")
            MockAIMessage.assert_called_once_with(content="test response")
            assert result == {"messages": [mock_ai_message]}

    def test_invoke_method_with_dict_message(self, mock_llm):
        """Test invoke method with dictionary format message."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        user_message = {"role": "user", "content": "test question"}
        
        with patch.object(agent, 'query', return_value="test response") as mock_query, \
             patch('langchain_core.messages.AIMessage') as MockAIMessage:
            
            mock_ai_message = Mock()
            MockAIMessage.return_value = mock_ai_message
            
            result = agent.invoke({"messages": [user_message]})
            
            mock_query.assert_called_once_with("test question")
            assert result == {"messages": [mock_ai_message]}

    def test_invoke_method_skip_transfer_messages(self, mock_llm):
        """Test invoke method skips transfer-related messages."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        transfer_message = Mock()
        transfer_message.content = "Successfully transferred to agent"
        
        user_message = Mock()
        user_message.content = "real user question"
        
        messages = [transfer_message, user_message]
        
        with patch.object(agent, 'query', return_value="test response") as mock_query, \
             patch('langchain_core.messages.AIMessage') as MockAIMessage:
            
            mock_ai_message = Mock()
            MockAIMessage.return_value = mock_ai_message
            
            result = agent.invoke({"messages": messages})
            
            mock_query.assert_called_once_with("real user question")

    def test_invoke_method_error_handling(self, mock_llm):
        """Test invoke method error handling."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        with patch.object(agent, 'query', side_effect=Exception("Query error")) as mock_query, \
             patch('langchain_core.messages.AIMessage') as MockAIMessage:
            
            mock_ai_message = Mock()
            MockAIMessage.return_value = mock_ai_message
            
            result = agent.invoke({"messages": [{"role": "user", "content": "test"}]})
            
            MockAIMessage.assert_called_once_with(content="Error processing request: Query error")

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self):
        """Test _initialize skips when already initialized."""
        agent = ConcreteSubAgentInterface()
        agent._initialized = True
        
        with patch.object(agent, '_setup_mcp_client', new_callable=AsyncMock) as mock_setup:
            await agent._initialize()
            mock_setup.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_success_flow(self, mock_llm):
        """Test successful initialization flow."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        with patch.object(agent, '_setup_mcp_client', new_callable=AsyncMock) as mock_setup, \
             patch.object(agent, '_load_tools', new_callable=AsyncMock) as mock_load_tools, \
             patch.object(agent, '_create_langgraph_agent', new_callable=AsyncMock) as mock_create_agent:
            
            await agent._initialize()
            
            mock_setup.assert_called_once()
            mock_load_tools.assert_called_once()
            mock_create_agent.assert_called_once()
            assert agent._initialized

    @pytest.mark.asyncio
    async def test_initialize_with_mcp_config_but_no_tools(self, mock_llm):
        """Test initialization fails when MCP config provided but no tools loaded."""
        agent = ConcreteSubAgentInterface(llm=mock_llm, mcp_config_path="/test/config.json")
        
        with patch.object(agent, '_setup_mcp_client', new_callable=AsyncMock), \
             patch.object(agent, '_load_tools', new_callable=AsyncMock), \
             patch.object(agent, '_create_langgraph_agent', new_callable=AsyncMock):
            
            # No tools loaded
            agent._tools = []
            
            with pytest.raises(AgentInitializationError) as exc_info:
                await agent._initialize()
            
            assert "requires MCP tools for analysis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_wraps_general_exceptions(self, mock_llm):
        """Test initialization wraps general exceptions in AgentInitializationError."""
        agent = ConcreteSubAgentInterface(llm=mock_llm)
        
        with patch.object(agent, '_setup_mcp_client', new_callable=AsyncMock) as mock_setup:
            mock_setup.side_effect = Exception("General error")
            
            with pytest.raises(AgentInitializationError) as exc_info:
                await agent._initialize()
            
            assert "Failed to initialize agent" in str(exc_info.value)
            assert exc_info.value.agent_type == "ConcreteSubAgentInterface"

    @pytest.mark.asyncio
    async def test_setup_mcp_client_no_config_path(self):
        """Test _setup_mcp_client skips when no config path provided."""
        agent = ConcreteSubAgentInterface()
        
        await agent._setup_mcp_client()
        
        assert agent._mcp_client is None
        assert not agent._mcp_config_loaded

    @pytest.mark.asyncio
    async def test_setup_mcp_client_success(self):
        """Test successful MCP client setup."""
        agent = ConcreteSubAgentInterface(mcp_config_path="/test/config.json")
        
        mock_config = {"test": "config"}
        mock_client_config = {"transformed": "config"}
        mock_client = Mock()
        mock_session_manager = Mock()
        mock_cleanup_manager = Mock()
        
        with patch('agentdk.agent.agent_interface.get_mcp_config', return_value=mock_config) as mock_get_config, \
             patch('agentdk.agent.agent_interface.transform_config_for_mcp_client', return_value=mock_client_config) as mock_transform, \
             patch('langchain_mcp_adapters.client.MultiServerMCPClient', return_value=mock_client) as MockClient, \
             patch('agentdk.agent.agent_interface.PersistentSessionManager', return_value=mock_session_manager) as MockSessionManager, \
             patch('agentdk.agent.agent_interface.CleanupManager', return_value=mock_cleanup_manager) as MockCleanupManager:
            
            mock_session_manager.initialize = AsyncMock()
            mock_cleanup_manager.register_cleanup = Mock()
            
            await agent._setup_mcp_client()
            
            mock_get_config.assert_called_once_with(agent)
            mock_transform.assert_called_once_with(mock_config)
            MockClient.assert_called_once_with(mock_client_config)
            MockSessionManager.assert_called_once_with(mock_client)
            mock_session_manager.initialize.assert_called_once()
            mock_cleanup_manager.register_cleanup.assert_called_once()
            
            assert agent._mcp_client == mock_client
            assert agent._mcp_config_loaded

    @pytest.mark.asyncio
    async def test_setup_mcp_client_error_handling(self):
        """Test MCP client setup error handling."""
        agent = ConcreteSubAgentInterface(mcp_config_path="/test/config.json")
        
        with patch('agentdk.agent.agent_interface.get_mcp_config', side_effect=Exception("Config error")):
            with pytest.raises(Exception):
                await agent._setup_mcp_client()

    @pytest.mark.asyncio
    async def test_load_tools_no_mcp_client(self):
        """Test _load_tools when no MCP client available."""
        agent = ConcreteSubAgentInterface()
        agent._mcp_client = None
        
        await agent._load_tools()
        
        assert agent._tools == []

    @pytest.mark.asyncio
    async def test_load_tools_success(self):
        """Test successful tool loading."""
        agent = ConcreteSubAgentInterface()
        agent._mcp_client = Mock()
        
        mock_tools = [Mock(), Mock()]
        wrapped_tools = [Mock(), Mock()]
        
        with patch.object(agent, '_get_tools_from_mcp', new_callable=AsyncMock, return_value=mock_tools) as mock_get_tools, \
             patch.object(agent, '_wrap_tools_with_logging', return_value=wrapped_tools) as mock_wrap:
            
            await agent._load_tools()
            
            mock_get_tools.assert_called_once()
            mock_wrap.assert_called_once_with(mock_tools)
            assert agent._tools == wrapped_tools

    @pytest.mark.asyncio
    async def test_load_tools_error_propagation(self):
        """Test _load_tools propagates exceptions."""
        agent = ConcreteSubAgentInterface()
        agent._mcp_client = Mock()
        
        with patch.object(agent, '_get_tools_from_mcp', new_callable=AsyncMock, side_effect=Exception("Tool error")):
            with pytest.raises(Exception, match="Tool error"):
                await agent._load_tools()

    @pytest.mark.asyncio
    async def test_get_tools_from_mcp_persistent_sessions(self):
        """Test getting tools using persistent sessions."""
        agent = ConcreteSubAgentInterface()
        agent._persistent_session_manager = Mock()
        agent._persistent_session_manager.is_initialized = True
        agent._persistent_session_manager.get_tools_persistent = AsyncMock(return_value=[Mock(), Mock()])
        
        tools = await agent._get_tools_from_mcp()
        
        agent._persistent_session_manager.get_tools_persistent.assert_called_once()
        assert len(tools) == 2

    @pytest.mark.asyncio
    async def test_get_tools_from_mcp_fallback_get_tools(self):
        """Test getting tools using fallback get_tools method."""
        agent = ConcreteSubAgentInterface()
        agent._mcp_client = Mock()
        agent._mcp_client.get_tools = AsyncMock(return_value=[Mock()])
        agent._persistent_session_manager = None
        
        tools = await agent._get_tools_from_mcp()
        
        assert len(tools) == 1

    @pytest.mark.asyncio
    async def test_get_tools_from_mcp_fallback_tools_property(self):
        """Test getting tools using fallback tools property."""
        agent = ConcreteSubAgentInterface()
        agent._mcp_client = Mock()
        agent._mcp_client.tools = [Mock(), Mock()]
        agent._persistent_session_manager = None
        # Remove get_tools method
        del agent._mcp_client.get_tools
        
        tools = await agent._get_tools_from_mcp()
        
        assert len(tools) == 2

    @pytest.mark.asyncio
    async def test_get_tools_from_mcp_no_interface(self):
        """Test getting tools when client has no tools interface."""
        agent = ConcreteSubAgentInterface()
        agent._mcp_client = Mock()
        agent._persistent_session_manager = None
        # Remove both get_tools method and tools property
        del agent._mcp_client.get_tools
        del agent._mcp_client.tools
        
        tools = await agent._get_tools_from_mcp()
        
        assert tools == []

    def test_wrap_tools_with_logging_success(self):
        """Test successful tool wrapping."""
        agent = ConcreteSubAgentInterface()
        
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool2 = Mock()
        mock_tool2.name = "tool2"
        
        wrapped_tool1 = Mock()
        wrapped_tool2 = Mock()
        
        with patch.object(agent, '_create_logging_wrapper', side_effect=[wrapped_tool1, wrapped_tool2]) as mock_wrap:
            result = agent._wrap_tools_with_logging([mock_tool1, mock_tool2])
            
            assert result == [wrapped_tool1, wrapped_tool2]
            assert mock_wrap.call_count == 2

    def test_wrap_tools_with_logging_partial_failure(self):
        """Test tool wrapping with some failures."""
        agent = ConcreteSubAgentInterface()
        
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool2 = Mock()
        mock_tool2.name = "tool2"
        
        wrapped_tool1 = Mock()
        
        with patch.object(agent, '_create_logging_wrapper', side_effect=[wrapped_tool1, Exception("Wrap error")]) as mock_wrap:
            result = agent._wrap_tools_with_logging([mock_tool1, mock_tool2])
            
            # Should include wrapped tool and original tool when wrapping fails
            assert result == [wrapped_tool1, mock_tool2]

    def test_create_logging_wrapper_with_func_attribute(self):
        """Test creating logging wrapper for tool with func attribute."""
        agent = ConcreteSubAgentInterface()
        
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.args_schema = None
        mock_tool.func = Mock()
        
        with patch('langchain_core.tools.StructuredTool') as MockStructuredTool, \
             patch.object(agent, '_create_wrapped_tool', return_value=Mock()) as mock_create:
            
            result = agent._create_logging_wrapper(mock_tool)
            
            mock_create.assert_called_once()

    def test_create_logging_wrapper_no_function(self):
        """Test creating logging wrapper when no function found."""
        agent = ConcreteSubAgentInterface()
        
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        # Remove function attributes
        del mock_tool.func
        del mock_tool._func
        del mock_tool.coroutine
        
        result = agent._create_logging_wrapper(mock_tool)
        
        # Should return original tool when no function found
        assert result == mock_tool

    def test_create_wrapped_tool_structured_tool(self):
        """Test creating wrapped tool using StructuredTool."""
        agent = ConcreteSubAgentInterface()
        
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test description"
        mock_tool.args_schema = None
        
        mock_wrapped_func = AsyncMock()
        mock_structured_tool = Mock()
        
        with patch('langchain_core.tools.StructuredTool', return_value=mock_structured_tool) as MockStructuredTool:
            result = agent._create_wrapped_tool(mock_tool, mock_wrapped_func)
            
            MockStructuredTool.assert_called_once_with(
                name="test_tool",
                description="Test description",
                args_schema=None,
                coroutine=mock_wrapped_func
            )
            assert result == mock_structured_tool

    def test_create_wrapped_tool_fallback_import(self):
        """Test creating wrapped tool with fallback import path."""
        agent = ConcreteSubAgentInterface()
        
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test description"
        mock_tool.args_schema = None
        
        mock_wrapped_func = Mock()
        mock_structured_tool = Mock()
        
        with patch('langchain_core.tools.StructuredTool', side_effect=ImportError), \
             patch('langchain.tools.StructuredTool', return_value=mock_structured_tool) as MockStructuredTool:
            
            result = agent._create_wrapped_tool(mock_tool, mock_wrapped_func)
            
            MockStructuredTool.assert_called_once_with(
                name="test_tool",
                description="Test description",
                args_schema=None,
                func=mock_wrapped_func
            )
            assert result == mock_structured_tool

    def test_create_wrapped_tool_no_structured_tool(self):
        """Test creating wrapped tool when StructuredTool not available."""
        agent = ConcreteSubAgentInterface()
        
        mock_tool = Mock()
        mock_wrapped_func = Mock()
        
        with patch('langchain_core.tools.StructuredTool', side_effect=ImportError), \
             patch('langchain.tools.StructuredTool', side_effect=ImportError):
            
            result = agent._create_wrapped_tool(mock_tool, mock_wrapped_func)
            
            # Should return original tool when StructuredTool not available
            assert result == mock_tool

    def test_sanitize_for_logging_string_values(self):
        """Test sanitizing string values for logging."""
        agent = ConcreteSubAgentInterface()
        
        # Short string
        short_str = "short string"
        result = agent._sanitize_for_logging(short_str)
        assert result == short_str
        
        # Long string
        long_str = "x" * 600
        result = agent._sanitize_for_logging(long_str)
        assert len(result) == 503  # 500 + "..."
        assert result.endswith("...")
    
    def test_sanitize_for_logging_non_string_values(self):
        """Test sanitizing non-string values for logging."""
        agent = ConcreteSubAgentInterface()
        
        # Integer
        result = agent._sanitize_for_logging(42)
        assert result == "42"
        
        # List
        result = agent._sanitize_for_logging([1, 2, 3])
        assert result == "[1, 2, 3]"
        
        # None
        result = agent._sanitize_for_logging(None)
        assert result == "None"

    @pytest.mark.asyncio
    async def test_logging_wrapper_async_function(self):
        """Test that logging wrapper handles async functions correctly."""
        agent = ConcreteSubAgentInterface()
        
        # Create a mock tool with an async function
        mock_tool = Mock()
        mock_tool.name = "async_tool"
        
        async def async_func(**kwargs):
            return "async result"
        
        mock_tool.func = async_func
        
        # Test the logging wrapper
        wrapped_tool = agent._create_logging_wrapper(mock_tool)
        
        # Should be able to create the wrapper without error
        assert wrapped_tool is not None

    @pytest.mark.asyncio
    async def test_logging_wrapper_sync_function(self):
        """Test that logging wrapper handles sync functions correctly."""
        agent = ConcreteSubAgentInterface()
        
        # Create a mock tool with a sync function
        mock_tool = Mock()
        mock_tool.name = "sync_tool"
        
        def sync_func(**kwargs):
            return "sync result"
        
        mock_tool.func = sync_func
        
        # Test the logging wrapper
        wrapped_tool = agent._create_logging_wrapper(mock_tool)
        
        # Should be able to create the wrapper without error
        assert wrapped_tool is not None