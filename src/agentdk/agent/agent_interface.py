"""Abstract agent interface for ML agents with MCP integration."""

import asyncio
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
from pathlib import Path

from ..core.mcp_load import get_mcp_config, transform_config_for_mcp_client
from ..core.logging_config import get_logger, ensure_nest_asyncio
from ..core.persistent_mcp import PersistentSessionManager, CleanupManager
from ..exceptions import AgentInitializationError, MCPConfigError


class AgentInterface(ABC):
    """Abstract base class for all ML agents."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, resume_session: Optional[bool] = None) -> None:
        """Initialize the agent with optional configuration.

        Args:
            config: Optional configuration dictionary for the agent
            resume_session: Whether to resume from previous session (None = no session management)
        """
        self.config = config or {}
        self.resume_session = resume_session

    @abstractmethod
    def query(self, user_prompt: str, **kwargs) -> str:
        """Process a user prompt and return a response.

        Args:
            user_prompt: The user's input prompt
            **kwargs: Additional keyword arguments for the query

        Returns:
            str: The agent's response
        """
        pass
    
    def _get_default_prompt(self) -> str:
        """Get the default system prompt for this agent type.

        Returns:
            Default system prompt for the agent
        """
        return "You are a helpful AI assistant."


class RootAgent(AgentInterface):
    """Root agent class for application-level agents.
    
    This class provides a foundation for agents that are used at the application 
    level, such as supervisor agents or main application agents. It includes
    basic initialization and configuration management.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        resume_session: Optional[bool] = None
    ) -> None:
        """Initialize the root agent.
        
        Args:
            config: Optional configuration dictionary for the agent
            resume_session: Whether to resume from previous session (None = no session management)
        """
        super().__init__(config, resume_session)






# Import MemoryAwareAgent to create memory-enabled SubAgent
# Note: Placed at end to avoid circular imports during module initialization
try:
    from ..memory.memory_aware_agent import MemoryAwareAgent
    
    class SubAgent(MemoryAwareAgent, ABC):
        """Memory-enabled SubAgent class that combines SubAgentInterface functionality with memory capabilities.
        
        This class provides the new unified agent interface that all subagents should inherit from.
        It combines the MCP integration capabilities of SubAgentInterface with the memory management
        capabilities of MemoryAwareAgent.
        """
        
        def __init__(
            self,
            llm: Any,
            config: Optional[Dict[str, Any]] = None,
            mcp_config_path: Optional[Union[str, Path]] = None,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            tools: Optional[List[Any]] = None,
            enable_memory: bool = True,
            resume_session: Optional[bool] = None,
            **kwargs: Any,
        ) -> None:
            """Initialize SubAgent with unified parameters and memory + MCP capabilities."""
            # Initialize memory system first
            super().__init__(
                llm=llm,
                config=config,
                name=name,
                prompt=prompt,
                enable_memory=enable_memory,
                resume_session=resume_session,
                **kwargs
            )
            
            # Add MCP-specific attributes from SubAgentInterface
            self._mcp_client: Optional[Any] = None
            self._mcp_config_path: Optional[Path] = (
                Path(mcp_config_path) if mcp_config_path else None
            )
            self._tools: List[Any] = tools or []
            self._initialized: bool = False
            self._mcp_config_loaded: bool = False
            self._persistent_session_manager: Optional[PersistentSessionManager] = None
            self._cleanup_manager: Optional[CleanupManager] = None
            self.agent: Optional[Any] = None
            self.logger = get_logger()
            ensure_nest_asyncio()

        @abstractmethod
        async def _create_langgraph_agent(self) -> None:
            """Create the LangGraph agent for this agent type."""
            pass

        async def _initialize(self) -> None:
            """Initialize MCP connections and load tools."""
            if self._initialized:
                self.logger.debug("Agent already initialized, skipping")
                return

            try:
                await self._setup_mcp_client()
                await self._load_tools()

                explicitly_requested_mcp = self._mcp_config_path is not None
                if explicitly_requested_mcp and not self._tools:
                    raise AgentInitializationError(
                        f"{self.__class__.__name__} requires MCP tools for analysis.",
                        agent_type=self.__class__.__name__,
                    )

                await self._create_langgraph_agent()
                self._initialized = True
                self.logger.debug(f"Agent {self.__class__.__name__} initialized successfully")

            except AgentInitializationError:
                raise
            except Exception as e:
                raise AgentInitializationError(
                    f"Failed to initialize agent {self.__class__.__name__}: {e}",
                    agent_type=self.__class__.__name__,
                ) from e

        async def _setup_mcp_client(self) -> None:
            """Set up MCP client from configuration path."""
            if not self._mcp_config_path:
                self.logger.debug("No MCP config path provided, skipping MCP client setup")
                return

            try:
                config = get_mcp_config(self)
                self._mcp_config_loaded = True
                client_config = transform_config_for_mcp_client(config)
                from langchain_mcp_adapters.client import MultiServerMCPClient
                self._mcp_client = MultiServerMCPClient(client_config)
                self.logger.debug(f"MCP client configured with {len(client_config)} servers")

                self._persistent_session_manager = PersistentSessionManager(self._mcp_client)
                await self._persistent_session_manager.initialize()
                self._cleanup_manager = CleanupManager(self._persistent_session_manager)
                self._cleanup_manager.register_cleanup()

            except Exception as e:
                self.logger.error(f"Failed to setup MCP client: {e}")
                raise

        async def _load_tools(self) -> None:
            """Load tools from MCP servers."""
            if not self._mcp_client:
                self.logger.warning("No MCP client available, skipping tool loading")
                return

            try:
                raw_tools = await self._get_tools_from_mcp()
                wrapped_tools = self._wrap_tools_with_logging(raw_tools)
                self._tools.extend(wrapped_tools)
                self.logger.debug(f"Loaded {len(self._tools)} tools from MCP servers")
            except Exception as e:
                self.logger.error(f"Failed to get tools from MCP client: {e}")
                raise

        async def _get_tools_from_mcp(self) -> List[Any]:
            """Get tools from MCP client using persistent sessions."""
            if (self._persistent_session_manager and 
                self._persistent_session_manager.is_initialized):
                self.logger.debug("Using persistent sessions to get tools")
                return await self._persistent_session_manager.get_tools_persistent()

            if not self._mcp_client:
                return []

            if hasattr(self._mcp_client, "get_tools"):
                return await self._mcp_client.get_tools()
            elif hasattr(self._mcp_client, "tools"):
                return self._mcp_client.tools
            else:
                return []

        def _wrap_tools_with_logging(self, tools: List[Any]) -> List[Any]:
            """Wrap all tools with unified logging capabilities."""
            return tools  # Simplified for now, can implement full logging wrapper later

        async def query_async(self, user_prompt: str, **kwargs: Any) -> str:
            """Async version of query for direct async usage."""
            try:
                if not self.is_initialized:
                    await self._initialize()

                actual_query, memory_context = self._parse_memory_context(user_prompt)

                if self.agent:
                    system_prompt = self.config.get("system_prompt", self._get_default_prompt())
                    if memory_context:
                        system_prompt += f"\n\nMEMORY CONTEXT:\n{memory_context}"
                    full_prompt = f"{system_prompt}\n\nUser Question: {actual_query}"
                    result = await self.agent.ainvoke({"messages": [full_prompt]})

                    if isinstance(result, dict) and "messages" in result:
                        last_message = result["messages"][-1]
                        return getattr(last_message, "content", str(last_message))
                    else:
                        return str(result)
                else:
                    agent_type = self.__class__.__name__.replace("Agent", "").upper()
                    return f"{agent_type} Analysis (without tools): {actual_query}"

            except AgentInitializationError:
                raise
            except Exception as e:
                self.logger.error(f"Error processing query: {e}")
                return f"Error processing query: {e}"

        def _parse_memory_context(self, user_prompt: str) -> tuple[str, str]:
            """Parse memory context from formatted user prompt."""
            if "User query: " in user_prompt and "Memory context: " in user_prompt:
                try:
                    parts = user_prompt.split("Memory context: ", 1)
                    if len(parts) == 2:
                        first_part = parts[0].strip()
                        if first_part.startswith("User query: "):
                            actual_query = first_part.replace("User query: ", "").strip()
                        else:
                            actual_query = first_part.strip()
                        memory_context = parts[1].strip()
                        return actual_query, memory_context
                except Exception as e:
                    self.logger.warning(f"Failed to parse memory context: {e}")
                    return user_prompt, ""
            return user_prompt, ""

        def invoke(self, state: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """Invoke method for LangGraph compatibility."""
            try:
                messages = state.get("messages", [])
                if not messages:
                    from langchain_core.messages import AIMessage
                    return {"messages": [AIMessage(content="No input provided")]}

                # Find user input from messages
                user_input = ""
                for message in messages:
                    if hasattr(message, "content") and hasattr(message, "type"):
                        if message.type in ("human", "user"):
                            user_input = message.content
                            break
                    elif isinstance(message, dict):
                        role = message.get("role", "")
                        if role in ("user", "human"):
                            user_input = message.get("content", "")
                            break

                if not user_input and messages:
                    last_message = messages[-1]
                    if hasattr(last_message, "content"):
                        user_input = last_message.content
                    elif isinstance(last_message, dict):
                        user_input = last_message.get("content", "")
                    else:
                        user_input = str(last_message)

                result = self.query(user_input)
                from langchain_core.messages import AIMessage
                return {"messages": [AIMessage(content=result)]}

            except Exception as e:
                self.logger.error(f"Error in invoke method: {e}")
                from langchain_core.messages import AIMessage
                return {"messages": [AIMessage(content=f"Error processing request: {e}")]}

        @property
        def tools(self) -> List[Any]:
            """Get the loaded and wrapped tools."""
            return self._tools

        @property
        def is_initialized(self) -> bool:
            """Check if the agent has been initialized."""
            return self._initialized

        def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
            """Process the current state and return updated state."""
            try:
                user_input = state.get('user_input', state.get('query', ''))
                if not user_input:
                    state['agent_output'] = "No user input provided"
                    return state

                result = self.query(user_input)
                state['agent_output'] = result
                state['agent_type'] = self.name or 'subagent'
                return state

            except Exception as e:
                error_msg = f"Agent processing error: {e}"
                self.logger.error(error_msg)
                state['agent_output'] = error_msg
                state['error'] = str(e)
                return state

    class SubAgentWithMCP(SubAgent):
        """Concrete SubAgent implementation with MCP capabilities.
        
        This class provides MCP integration for agents that need to interact with
        MCP servers for tools and capabilities.
        """
        
        def __init__(
            self,
            llm: Any,
            mcp_config_path: Union[str, Path],
            config: Optional[Dict[str, Any]] = None,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            enable_memory: bool = True,
            resume_session: Optional[bool] = None,
            **kwargs: Any,
        ) -> None:
            """Initialize SubAgentWithMCP.
            
            Args:
                llm: Language model instance (required)
                mcp_config_path: Path to MCP configuration file (required)
                config: Optional configuration dictionary
                name: Optional agent name
                prompt: Optional system prompt
                enable_memory: Whether to enable memory capabilities
                resume_session: Whether to resume from previous session
                **kwargs: Additional configuration parameters
                
            Raises:
                ValueError: If mcp_config_path is not provided
            """
            if not mcp_config_path:
                raise ValueError("mcp_config_path is required for SubAgentWithMCP")
            
            # Resolve MCP config path
            resolved_path = self._resolve_mcp_config_path(mcp_config_path)
            
            # Initialize with MCP configuration
            super().__init__(
                llm=llm,
                config=config,
                mcp_config_path=resolved_path,
                name=name,
                prompt=prompt,
                enable_memory=enable_memory,
                resume_session=resume_session,
                **kwargs
            )
        
        def _resolve_mcp_config_path(self, mcp_config_path: Union[str, Path]) -> Path:
            """Resolve MCP config path relative to the agent's file location.
            
            Args:
                mcp_config_path: Relative or absolute path to MCP config
                
            Returns:
                Resolved absolute path to MCP config
            """
            config_path = Path(mcp_config_path)
            
            # If it's already absolute, return as-is
            if config_path.is_absolute():
                return config_path.resolve()
            
            # For relative paths, resolve relative to the agent's file location
            try:
                # Get the file where this agent class is defined
                agent_file = inspect.getfile(self.__class__)
                agent_dir = Path(agent_file).parent
                
                # Resolve the config path relative to agent directory
                resolved_path = (agent_dir / config_path).resolve()
                
                return resolved_path
                
            except (OSError, TypeError):
                # Fallback to resolving relative to current working directory
                return config_path.resolve()
    
    class SubAgentWithoutMCP(SubAgent):
        """Concrete SubAgent implementation without MCP.
        
        This class provides functionality for agents that work with external APIs,
        web services, or other non-MCP tools.
        """
        
        def __init__(
            self,
            llm: Any,
            config: Optional[Dict[str, Any]] = None,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            tools: Optional[List[Any]] = None,
            enable_memory: bool = True,
            resume_session: Optional[bool] = None,
            **kwargs: Any,
        ) -> None:
            """Initialize SubAgentWithoutMCP.
            
            Args:
                llm: Language model instance (required)
                config: Optional configuration dictionary
                name: Optional agent name
                prompt: Optional system prompt
                tools: Optional list of external tools
                enable_memory: Whether to enable memory capabilities
                resume_session: Whether to resume from previous session
                **kwargs: Additional configuration parameters
            """
            # Initialize without MCP configuration
            super().__init__(
                llm=llm,
                config=config,
                mcp_config_path=None,  # No MCP
                name=name,
                prompt=prompt,
                tools=tools or [],
                enable_memory=enable_memory,
                resume_session=resume_session,
                **kwargs
            )

except ImportError:
    # If MemoryAwareAgent is not available, create a placeholder
    class SubAgent:
        """Placeholder SubAgent class when MemoryAwareAgent is not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("MemoryAwareAgent not available. Please check your installation.")
    
    class SubAgentWithMCP(SubAgent):
        """Placeholder SubAgentWithMCP class when MemoryAwareAgent is not available."""
        pass
    
    class SubAgentWithoutMCP(SubAgent):
        """Placeholder SubAgentWithoutMCP class when MemoryAwareAgent is not available."""
        pass
