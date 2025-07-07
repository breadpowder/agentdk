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


class SubAgentInterface(AgentInterface):
    """Abstract base class for subagents with MCP integration and async support.

    This enhanced interface provides:
    - Async initialization pattern
    - MCP server loading and management
    - Tool wrapping with logging capabilities
    - LLM and prompt management
    - LangGraph agent creation and query processing
    - IPython/Jupyter compatibility
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        mcp_config_path: Optional[Union[str, Path]] = None,
        llm: Optional[Any] = None,
        prompt: Optional[str] = None,
        resume_session: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the subagent with MCP integration support.

        Args:
            config: Optional configuration dictionary
            mcp_config_path: Optional path to MCP configuration file
            llm: Language model instance
            prompt: System prompt for the agent
            resume_session: Whether to resume from previous session (None = no session management)
            **kwargs: Additional configuration parameters
        """
        # Prepare config with LLM and prompt
        if config is None:
            config = kwargs.get("config", {})

        # Handle prompt configuration
        if prompt:
            config["system_prompt"] = prompt
        elif "system_prompt" not in config:
            config["system_prompt"] = self._get_default_prompt()

        # Handle LLM configuration
        if llm:
            config["llm"] = llm

        super().__init__(config, resume_session)

        # MCP integration attributes
        self._mcp_client: Optional[Any] = None
        self._mcp_config_path: Optional[Path] = (
            Path(mcp_config_path) if mcp_config_path else None
        )
        self._tools: List[Any] = kwargs.get("tools", [])
        self._initialized: bool = False
        self._mcp_config_loaded: bool = False

        # Persistent session management
        self._persistent_session_manager: Optional[PersistentSessionManager] = None
        self._cleanup_manager: Optional[CleanupManager] = None

        # LLM and agent attributes
        self.llm: Optional[Any] = llm
        self.agent: Optional[Any] = None
        self.name: Optional[str] = kwargs.get("name", None)

        # Logger setup
        self.logger = get_logger()

        # Ensure async compatibility
        ensure_nest_asyncio()

    @abstractmethod
    def _get_default_prompt(self) -> str:
        """Get the default system prompt for this agent type.

        Returns:
            Default system prompt for the agent
        """
        pass

    @abstractmethod
    async def _create_langgraph_agent(self) -> None:
        """Create the LangGraph agent for this agent type.

        This method should create self.agent using the LLM and tools.
        Each agent type implements its own specific agent creation logic.
        """
        pass

    async def _initialize(self) -> None:
        """Initialize MCP connections and load tools.

        This method should be called after agent creation to set up MCP servers
        and load available tools. Subclasses can override this to add custom
        initialization logic.

        Raises:
            AgentInitializationError: If initialization fails
        """
        if self._initialized:
            self.logger.debug("Agent already initialized, skipping")
            return

        try:
            # Always load MCP configuration from config path
            await self._setup_mcp_client()

            # Load and wrap tools
            await self._load_tools()

            # Validate MCP requirements - only require tools if explicitly requested
            explicitly_requested_mcp = self._mcp_config_path is not None

            if explicitly_requested_mcp and not self._tools:
                raise AgentInitializationError(
                    f"{self.__class__.__name__} requires MCP tools for analysis. "
                    "MCP configuration was explicitly provided but no tools were loaded. "
                    "Check MCP server connectivity and configuration.",
                    agent_type=self.__class__.__name__,
                )

            # Create LangGraph agent (agent-specific implementation)
            await self._create_langgraph_agent()

            self._initialized = True
            self.logger.debug(
                f"Agent {self.__class__.__name__} initialized successfully"
            )

        except AgentInitializationError:
            # Re-raise AgentInitializationError as-is
            raise
        except Exception as e:
            # Wrap other exceptions in AgentInitializationError
            raise AgentInitializationError(
                f"Failed to initialize agent {self.__class__.__name__}: {e}",
                agent_type=self.__class__.__name__,
            ) from e

    def query(self, user_prompt: str, **kwargs: Any) -> str:
        """Process a user query for this agent type.

        Args:
            user_prompt: The user's question or request
            **kwargs: Additional parameters

        Returns:
            Analysis result as a string
        """
        # Ensure nest_asyncio is applied globally for nested event loop support
        ensure_nest_asyncio()

        # Apply nest_asyncio to allow nested asyncio.run() calls
        # This prevents the event loop boundary issues with persistent sessions
        import nest_asyncio

        nest_asyncio.apply()

        try:
            # With nest_asyncio applied, we can safely use asyncio.run even
            # if there's already a running loop (like in Jupyter/IPython)
            # This maintains session consistency across calls
            return asyncio.run(self.query_async(user_prompt, **kwargs))

        except Exception as e:
            # If async execution fails, provide detailed error information
            self.logger.error(f"Query execution failed: {e}")
            return f"Query execution failed: {e}"

    def invoke(
        self, state: Dict[str, Any], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Invoke method for LangGraph compatibility.

        This method provides compatibility with langgraph_supervisor and other LangGraph workflows.
        It expects a state dictionary and returns an updated state dictionary.

        Args:
            state: State dictionary from LangGraph workflow
            config: Optional configuration dictionary

        Returns:
            Updated state dictionary with messages
        """
        try:
            # Extract messages from state
            messages = state.get("messages", [])

            if not messages:
                # If no messages, return state with an empty message
                from langchain_core.messages import AIMessage

                return {"messages": [AIMessage(content="No input provided")]}

            # Find the user's original question by looking for the first user message
            # This handles supervisor handoff scenarios where transfer messages are added
            user_input = ""
            for message in messages:
                if hasattr(message, "content") and hasattr(message, "type"):
                    # LangChain message object
                    if message.type == "human" or message.type == "user":
                        user_input = message.content
                        break
                elif isinstance(message, dict):
                    # Dictionary format message
                    role = message.get("role", "")
                    if role == "user" or role == "human":
                        user_input = message.get("content", "")
                        break

            # Fallback: if no user message found, use the last non-transfer message
            if not user_input:
                for message in reversed(messages):
                    if hasattr(message, "content"):
                        content = message.content
                    elif isinstance(message, dict):
                        content = message.get("content", "")
                    else:
                        content = str(message)

                    # Skip transfer-related messages
                    if content and not any(
                        keyword in content.lower()
                        for keyword in [
                            "transferred",
                            "transfer_to_",
                            "successfully transferred",
                        ]
                    ):
                        user_input = content
                        break

            # Final fallback: use last message if nothing else found
            if not user_input:
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    user_input = last_message.content
                elif isinstance(last_message, dict):
                    user_input = last_message.get("content", "")
                else:
                    user_input = str(last_message)

            # Process the query
            result = self.query(user_input)

            # Return the result in the correct format for supervisor compatibility
            from langchain_core.messages import AIMessage

            return {"messages": [AIMessage(content=result)]}

        except Exception as e:
            self.logger.error(f"Error in invoke method: {e}")
            from langchain_core.messages import AIMessage

            return {"messages": [AIMessage(content=f"Error processing request: {e}")]}

    async def query_async(self, user_prompt: str, **kwargs: Any) -> str:
        """Async version of query for direct async usage.

        Args:
            user_prompt: The user's question or request
            **kwargs: Additional parameters

        Returns:
            Analysis result as a string
        """
        try:
            # Ensure agent is initialized
            if not self.is_initialized:
                await self._initialize()

            # Parse memory context if present in the user prompt
            actual_query, memory_context = self._parse_memory_context(user_prompt)

            # If we have a LangGraph agent, use it
            if self.agent:
                # Combine system prompt with user prompt
                system_prompt = self.config.get(
                    "system_prompt", self._get_default_prompt()
                )

                # Add memory context to system prompt if available
                if memory_context:
                    system_prompt += f"\n\nMEMORY CONTEXT:\n{memory_context}"

                full_prompt = f"{system_prompt}\n\nUser Question: {actual_query}"

                # Use LangGraph agent to process the query
                result = await self.agent.ainvoke({"messages": [full_prompt]})

                # Extract the response from LangGraph result
                if isinstance(result, dict) and "messages" in result:
                    last_message = result["messages"][-1]
                    return getattr(last_message, "content", str(last_message))
                else:
                    return str(result)
            else:
                # Fallback for when no agent is available
                agent_type = self.__class__.__name__.replace("Agent", "").upper()
                return f"{agent_type} Analysis (without tools): {actual_query}\n\nNote: No tools available. Please configure MCP servers for full functionality."

        except AgentInitializationError:
            # Re-raise initialization errors - these are critical and should not be silently handled
            raise
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return f"Error processing query: {e}"

    def _parse_memory_context(self, user_prompt: str) -> tuple[str, str]:
        """Parse memory context from formatted user prompt.

        Args:
            user_prompt: User prompt that may contain memory context

        Returns:
            Tuple of (actual_query, memory_context)
        """
        # Check if the prompt contains memory context formatting
        if "User query: " in user_prompt and "Memory context: " in user_prompt:
            try:
                # Split by the first occurrence of "Memory context:"
                parts = user_prompt.split("Memory context: ", 1)
                if len(parts) == 2:
                    # Extract the user query from the first part
                    first_part = parts[0].strip()
                    if first_part.startswith("User query: "):
                        actual_query = first_part.replace("User query: ", "").strip()
                    else:
                        actual_query = first_part.strip()

                    # The memory context is everything after "Memory context: "
                    memory_context = parts[1].strip()

                    return actual_query, memory_context

            except Exception as e:
                self.logger.warning(f"Failed to parse memory context: {e}")
                return user_prompt, ""

        # No memory context found, return original prompt
        return user_prompt, ""

    async def _setup_mcp_client(self) -> None:
        """Set up MCP client from configuration path.

        Only attempts to load MCP client if mcp_config_path was provided.

        Raises:
            MCPConfigError: If configuration loading fails when path is provided
        """
        # Skip MCP setup if no config path provided
        if not self._mcp_config_path:
            self.logger.debug("No MCP config path provided, skipping MCP client setup")
            return

        try:
            # Load MCP configuration using shared utilities
            config = get_mcp_config(self)

            # Mark that MCP configuration was successfully loaded
            self._mcp_config_loaded = True

            # Transform configuration for MCP client
            client_config = transform_config_for_mcp_client(config)

            # Import and setup MCP client (fail fast on missing dependencies)
            from langchain_mcp_adapters.client import MultiServerMCPClient

            # Create MCP adapter/client
            self._mcp_client = MultiServerMCPClient(client_config)

            self.logger.debug(f"MCP client configured with {len(client_config)} servers")

            # Create persistent session manager
            self._persistent_session_manager = PersistentSessionManager(
                self._mcp_client
            )

            # Initialize persistent sessions
            await self._persistent_session_manager.initialize()

            # Set up cleanup management
            self._cleanup_manager = CleanupManager(self._persistent_session_manager)
            self._cleanup_manager.register_cleanup()

            self.logger.debug(
                f"Persistent session manager initialized with {self._persistent_session_manager.active_session_count} active sessions"
            )

        except Exception as e:
            self.logger.error(f"Failed to setup MCP client: {e}")
            raise

    async def _load_tools(self) -> None:
        """Load tools from MCP servers and wrap them with logging."""
        if not self._mcp_client:
            self.logger.warning("No MCP client available, skipping tool loading")
            return

        try:
            # Get tools from MCP client
            raw_tools = await self._get_tools_from_mcp()

            # Wrap tools with logging
            wrapped_tools = self._wrap_tools_with_logging(raw_tools)
            self._tools.extend(wrapped_tools)

            self.logger.debug(f"Loaded {len(self._tools)} tools from MCP servers")

        except Exception as e:
            self.logger.error(f"Failed to get tools from MCP client: {e}")
            # Re-raise the exception - subclasses can decide how to handle this
            raise

    async def _get_tools_from_mcp(self) -> List[Any]:
        """Get tools from MCP client using persistent sessions.

        This method uses persistent sessions instead of creating ephemeral sessions
        for each tool call, solving the performance overhead issue.

        Returns:
            List of tools from MCP servers

        Raises:
            Exception: If MCP client fails to provide tools
        """
        # Use persistent session manager if available
        if (
            self._persistent_session_manager
            and self._persistent_session_manager.is_initialized
        ):
            self.logger.debug("Using persistent sessions to get tools")
            return await self._persistent_session_manager.get_tools_persistent()

        # Fallback to original ephemeral approach (for backward compatibility)
        if not self._mcp_client:
            self.logger.warning("No MCP client available")
            return []

        self.logger.warning(
            "Falling back to ephemeral sessions (persistent session manager not available)"
        )

        # Try the standard MCP client interface (creates ephemeral sessions)
        if hasattr(self._mcp_client, "get_tools"):
            return await self._mcp_client.get_tools()
        elif hasattr(self._mcp_client, "tools"):
            return self._mcp_client.tools
        else:
            self.logger.error("MCP client does not provide tools interface")
            return []

    def _wrap_tools_with_logging(self, tools: List[Any]) -> List[Any]:
        """Wrap all tools with unified logging capabilities.

        Args:
            tools: List of tools to wrap

        Returns:
            List of wrapped tools with logging
        """
        wrapped_tools = []

        for tool in tools:
            try:
                wrapped_tool = self._create_logging_wrapper(tool)
                wrapped_tools.append(wrapped_tool)
            except Exception as e:
                self.logger.warning(
                    f"Failed to wrap tool {getattr(tool, 'name', 'unknown')}: {e}"
                )
                # Include original tool if wrapping fails
                wrapped_tools.append(tool)

        return wrapped_tools

    def _create_logging_wrapper(self, tool: Any) -> Any:
        """Create a unified logging wrapper for any tool type.

        Args:
            tool: Tool to wrap

        Returns:
            Wrapped tool with logging
        """
        # Try multiple function attribute patterns for different tool types
        original_func = (
            getattr(tool, "func", None)
            or getattr(tool, "_func", None)
            or getattr(tool, "coroutine", None)  # StructuredTool from MCP adapters
        )

        if not original_func:
            self.logger.warning(
                f"Could not find function for tool {getattr(tool, 'name', 'unknown')}"
            )
            return tool

        async def logged_invoke(**kwargs):
            # Log tool execution in JSON format
            import json

            log_data = {
                "tool": getattr(tool, "name", "unknown_tool"),
                "args": {k: self._sanitize_for_logging(v) for k, v in kwargs.items()},
            }
            self.logger.info(json.dumps(log_data))

            try:
                # Execute original tool
                if asyncio.iscoroutinefunction(original_func):
                    result = await original_func(**kwargs)
                else:
                    result = original_func(**kwargs)

                # Log completion in JSON format
                completion_data = {
                    "tool": getattr(tool, "name", "unknown_tool"),
                    "status": "successful",
                }
                self.logger.info(json.dumps(completion_data))
                return result

            except Exception as e:
                # Log error in JSON format
                error_data = {
                    "tool": getattr(tool, "name", "unknown_tool"),
                    "status": "failed",
                    "error": str(e),
                }
                self.logger.error(json.dumps(error_data))
                raise

        # Create new tool with wrapped function
        return self._create_wrapped_tool(tool, logged_invoke)

    def _create_wrapped_tool(self, original_tool: Any, wrapped_func: Any) -> Any:
        """Create a new tool with wrapped function.

        Args:
            original_tool: Original tool to wrap
            wrapped_func: Wrapped function

        Returns:
            New tool with wrapped function
        """
        # This implementation depends on the specific tool type
        # For LangChain tools, we'd use StructuredTool
        try:
            from langchain_core.tools import StructuredTool

            return StructuredTool(
                name=getattr(original_tool, "name", "unknown_tool"),
                description=getattr(original_tool, "description", "Tool with logging"),
                args_schema=getattr(original_tool, "args_schema", None),
                coroutine=wrapped_func,  # Use coroutine instead of func for async tools
            )
        except ImportError:
            try:
                # Fallback to older import path
                from langchain.tools import StructuredTool

                return StructuredTool(
                    name=getattr(original_tool, "name", "unknown_tool"),
                    description=getattr(
                        original_tool, "description", "Tool with logging"
                    ),
                    args_schema=getattr(original_tool, "args_schema", None),
                    func=wrapped_func,
                )
            except ImportError:
                # Final fallback: return original tool if StructuredTool not available
                self.logger.warning(
                    "StructuredTool not available, returning original tool"
                )
                return original_tool

    def _sanitize_for_logging(self, value: Any) -> str:
        """Sanitize any value for safe logging.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized value safe for logging
        """
        # Return the value as-is for debugging purposes
        if not isinstance(value, str):
            return str(value)

        # Just limit length if too long, but keep the actual content
        if len(value) > 500:
            return value[:500] + "..."

        return value

    @property
    def tools(self) -> List[Any]:
        """Get the loaded and wrapped tools.

        Returns:
            List of available tools
        """
        return self._tools

    @property
    def is_initialized(self) -> bool:
        """Check if the agent has been initialized.

        Returns:
            bool: True if agent is initialized
        """
        return self._initialized

    @abstractmethod
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state and return updated state.

        Args:
            state: Current state dictionary from the graph

        Returns:
            Dict[str, Any]: Updated state dictionary
        """
        pass


class SubAgentWithMCP(SubAgentInterface):
    """Subagent that requires MCP configuration for tool loading.
    
    This class is designed for agents that need MCP tools to function properly,
    such as database agents, SQL agents, or file system agents.
    """
    
    def __init__(
        self,
        llm: Any,
        mcp_config_path: Union[str, Path],
        config: Optional[Dict[str, Any]] = None,
        prompt: Optional[str] = None,
        resume_session: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the MCP-enabled subagent.

        Args:
            llm: Language model instance (required)
            mcp_config_path: Path to MCP configuration file (required)
            config: Optional configuration dictionary
            prompt: System prompt for the agent
            resume_session: Whether to resume from previous session (None = no session management)
            **kwargs: Additional configuration parameters
            
        Raises:
            ValueError: If mcp_config_path is not provided
        """
        if not mcp_config_path:
            raise ValueError("mcp_config_path is required for SubAgentWithMCP")
        
        # Set up logger early so it's available for path resolution
        from ..core.logging_config import set_log_level
        set_log_level("INFO")  # Set default log level
        self.logger = get_logger()
        
        # Resolve the MCP config path relative to the agent's location
        resolved_path = self._resolve_mcp_config_path(mcp_config_path)
        
        # Pass the resolved path to the parent constructor
        super().__init__(
            config=config,
            mcp_config_path=resolved_path,
            llm=llm,
            prompt=prompt,
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
            
            self.logger.debug(f"Resolved MCP config path: {config_path} -> {resolved_path}")
            return resolved_path
            
        except (OSError, TypeError) as e:
            self.logger.warning(f"Could not determine agent file location: {e}")
            # Fallback to resolving relative to current working directory
            return config_path.resolve()


class SubAgentWithoutMCP(SubAgentInterface):
    """Subagent that does not require MCP configuration.
    
    This class is designed for agents that work with external APIs,
    web services, or other non-MCP tools.
    """
    
    def __init__(
        self,
        llm: Any,
        config: Optional[Dict[str, Any]] = None,
        prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        resume_session: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the non-MCP subagent.

        Args:
            llm: Language model instance (required)
            config: Optional configuration dictionary
            prompt: System prompt for the agent
            tools: Optional list of tools to use (e.g., web search, APIs)
            resume_session: Whether to resume from previous session (None = no session management)
            **kwargs: Additional configuration parameters
        """
        # Ensure MCP config path is None for this agent type
        super().__init__(
            config=config,
            mcp_config_path=None,
            llm=llm,
            prompt=prompt,
            resume_session=resume_session,
            tools=tools or [],
            **kwargs
        )
    
    async def _initialize(self) -> None:
        """Initialize the agent without MCP setup.
        
        Overrides the parent method to skip MCP initialization entirely.
        """
        if self._initialized:
            self.logger.debug("Agent already initialized, skipping")
            return

        try:
            # Skip MCP setup completely - no MCP client or tools from MCP
            # Just use any tools that were provided directly
            self.logger.debug(f"Initializing agent with {len(self._tools)} provided tools")
            
            # Create LangGraph agent (agent-specific implementation)
            await self._create_langgraph_agent()

            self._initialized = True
            self.logger.debug(
                f"Agent {self.__class__.__name__} initialized successfully (no MCP)"
            )

        except Exception as e:
            # Wrap exceptions in AgentInitializationError
            raise AgentInitializationError(
                f"Failed to initialize agent {self.__class__.__name__}: {e}",
                agent_type=self.__class__.__name__,
            ) from e
