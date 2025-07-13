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


def create_memory_session(
    name: Optional[str] = None,
    user_id: str = "default",
    enable_memory: bool = True,
    memory_config: Optional[Dict[str, Any]] = None,
    require_memory: bool = False
) -> Optional[Any]:
    """Factory function for dependency injection with proper error handling.
    
    Args:
        name: Optional memory session name
        user_id: User identifier for scoped memory
        enable_memory: Whether to enable memory functionality
        memory_config: Optional memory configuration
        require_memory: If True, raises error when memory unavailable (fail-fast)
        
    Returns:
        MemoryAwareSession instance if enabled and available, None otherwise
        
    Raises:
        AgentInitializationError: If memory required but dependencies unavailable
    """
    if not enable_memory:
        return None
        
    try:
        from ..memory.memory_aware_agent import MemoryAwareSession
        from ..core.logging_config import get_logger
        
        logger = get_logger()
        logger.debug(f"Creating memory session: name={name}, user_id={user_id}")
        
        return MemoryAwareSession(
            name=name,
            user_id=user_id,
            memory_config=memory_config
        )
        
    except ImportError as e:
        from ..core.logging_config import get_logger
        from ..exceptions import AgentInitializationError
        
        logger = get_logger()
        error_msg = f"Memory functionality unavailable: {e}"
        
        if require_memory:
            logger.error(error_msg)
            raise AgentInitializationError(
                "Memory functionality explicitly required but dependencies not available. "
                "Install memory dependencies or set enable_memory=False."
            ) from e
        else:
            logger.warning(f"{error_msg}. Continuing without memory functionality.")
            return None
            
    except Exception as e:
        from ..core.logging_config import get_logger
        from ..exceptions import AgentInitializationError
        
        logger = get_logger()
        logger.error(f"Failed to create memory session: {e}")
        
        if require_memory:
            raise AgentInitializationError(
                f"Failed to create required memory session: {e}"
            ) from e
        else:
            logger.warning(f"Memory session creation failed: {e}. Continuing without memory.")
            return None


class AgentInterface(ABC):
    """Abstract base class for all ML agents with dependency injection."""

    def __init__(
        self, 
        memory_session: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        resume_session: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        """Initialize the agent with dependency injection.

        Args:
            memory_session: Injected memory session (dependency injection)
            config: Optional configuration dictionary for the agent
            resume_session: Whether to resume from previous session (None = no session management)
            **kwargs: Additional keyword arguments
        """
        self.memory_session = memory_session
        self.config = config or {}
        self.resume_session = resume_session

    @abstractmethod
    def query(self, user_prompt: str, **kwargs) -> str:
        """Primary interface: Process user prompt and return response.

        Args:
            user_prompt: The user's input prompt
            **kwargs: Additional keyword arguments for the query

        Returns:
            str: The agent's response
        """
        pass
    
    def __call__(self, user_prompt: str, **kwargs) -> str:
        """Syntax sugar: Calls query() for convenience."""
        return self.query(user_prompt, **kwargs)
    
    def _get_default_prompt(self) -> str:
        """Get default system prompt for agent type."""
        return "You are a helpful AI assistant."
    
    # MEMORY UTILITIES (when memory_session is injected)
    def get_memory_context(self, query: str) -> Optional[str]:
        """Get memory context if memory session available."""
        return self.memory_session.get_memory_context(query) if self.memory_session else None

    def store_interaction(self, query: str, response: str) -> None:
        """Store interaction if memory session available."""
        if self.memory_session:
            self.memory_session.store_interaction(query, response)

    def get_memory_aware_prompt(self, base_prompt: str) -> str:
        """Enhance prompt with memory context if available."""
        if self.memory_session:
            memory_context = self.memory_session.get_memory_context(base_prompt)
            if memory_context:
                return f"{memory_context}\n\n{base_prompt}"
        return base_prompt


class App(ABC):
    """Application base class with pure application concerns."""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        **kwargs: Any
    ):
        """Initialize application.
        
        Args:
            config: Optional configuration dictionary
            name: Optional application name
            **kwargs: Additional keyword arguments
        """
        self.config = config or {}
        self.name = name
    
    @abstractmethod
    def create_workflow(self, llm: Any) -> Any:
        """Create and return workflow instance."""
        pass
    
    @abstractmethod
    def clean_app(self) -> None:
        """Cleanup application resources."""
        pass


class RootAgent(App, AgentInterface):
    """Root agent with multiple inheritance: App + AgentInterface.
    
    Combines application logic + agent interface for applications that need agent capabilities.
    """
    
    def __init__(
        self,
        memory_session: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        resume_session: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        """Initialize root agent with multiple inheritance.
        
        Args:
            memory_session: Injected memory session (dependency injection)
            config: Optional configuration dictionary
            name: Optional agent name
            resume_session: Whether to resume from previous session
            **kwargs: Additional keyword arguments
        """
        # Initialize both parent classes
        App.__init__(self, config=config, name=name, **kwargs)
        AgentInterface.__init__(self, memory_session=memory_session, config=config, resume_session=resume_session, **kwargs)
    
    def query(self, user_prompt: str, **kwargs) -> str:
        """Concrete implementation combining app logic + agent interface."""
        # Memory integration
        if self.memory_session:
            enhanced_input = self.memory_session.process_with_memory(user_prompt)
            response = self._process_query(user_prompt, enhanced_input)
            return self.memory_session.finalize_with_memory(user_prompt, response)
        else:
            return self._process_query(user_prompt, {})
    
    @abstractmethod  
    def _process_query(self, user_prompt: str, enhanced_input: Dict) -> str:
        """Subclasses implement processing logic."""
        pass






# Import MemoryAwareAgent to create memory-enabled SubAgent
# Note: Placed at end to avoid circular imports during module initialization
try:
    from ..memory.memory_aware_agent import MemoryAwareSession
    
    class SubAgent(AgentInterface, ABC):
        """Individual agent implementations with dependency injection.
        
        SubAgent inherits from AgentInterface and implements agent-specific functionality
        with dependency injection for memory sessions.
        """
        
        def __init__(
            self,
            llm: Any,
            memory_session: Optional[Any] = None,
            config: Optional[Dict[str, Any]] = None,
            mcp_config_path: Optional[Union[str, Path]] = None,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            tools: Optional[List[Any]] = None,
            resume_session: Optional[bool] = None,
            **kwargs: Any,
        ) -> None:
            """Initialize SubAgent with dependency injection.
            
            Args:
                llm: Language model instance (required)
                memory_session: Injected memory session (dependency injection)
                config: Optional configuration dictionary
                mcp_config_path: Optional MCP configuration path
                name: Optional agent identifier
                prompt: Optional agent system prompt
                tools: Optional available tools
                resume_session: Whether to resume from previous session
                **kwargs: Additional keyword arguments
            """
            # Initialize with dependency injection
            super().__init__(
                memory_session=memory_session,
                config=config,
                resume_session=resume_session,
                **kwargs
            )
            
            # Agent-specific attributes
            self.llm = llm
            self.name = name or self.__class__.__name__.lower().replace('agent', '')

            if prompt is None:
                raise ValueError("prompt cannot be None for SubAgent")
            self.prompt = prompt
            
            # MCP-specific attributes
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

        def query(self, user_prompt: str, **kwargs) -> str:
            """FIXED: Concrete implementation with LLM integration (sync wrapper)."""
            # Synchronous wrapper for async implementation
            import asyncio
            import nest_asyncio
            
            # Apply nest_asyncio to allow nested asyncio.run() calls
            # This prevents event loop boundary issues with LangGraph supervisor
            nest_asyncio.apply()
            
            try:
                if asyncio.iscoroutinefunction(self.query_async):
                    return asyncio.run(self.query_async(user_prompt, **kwargs))
                else:
                    # Memory integration
                    if self.memory_session:
                        enhanced_input = self.memory_session.process_with_memory(user_prompt)
                        response = self._execute_with_llm(user_prompt, enhanced_input)
                        return self.memory_session.finalize_with_memory(user_prompt, response)
                    else:
                        return self._execute_with_llm(user_prompt, {})
            except Exception as e:
                import traceback
                self.logger.error(f"Query execution failed: {e}")
                self.logger.error(f"Stack trace:\n{traceback.format_exc()}")
                return f"Query execution failed: {e}"
        
        @abstractmethod
        def _execute_with_llm(self, user_prompt: str, enhanced_input: Dict) -> str:
            """Subclasses implement LLM execution logic."""
            pass
        
        async def _create_langgraph_agent(self) -> None:
            """Create LangGraph reactive agent with available tools."""
            try:
                from langgraph.prebuilt import create_react_agent

                # Create react agent with LLM and tools
                self.agent = create_react_agent(self.llm, self._tools)

                self.logger.info(f"Created LangGraph agent with {len(self._tools)} tools")

            except ImportError as e:
                self.logger.error(f"Failed to import LangGraph: {e}")
            except Exception as e:
                self.logger.error(f"Failed to create LangGraph agent: {e}")
                raise

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

        async def query_async(self, user_prompt: str, **kwargs: Any) -> str:
            """Async version of query for direct async usage."""
            try:
                if not self.is_initialized:
                    await self._initialize()

                actual_query, memory_context = self._parse_memory_context(user_prompt)

                if self.agent:
                    from langchain_core.messages import HumanMessage, SystemMessage
                    
                    system_prompt = self.prompt
                    self.logger.debug(f"Using system prompt: {system_prompt[:100]}...")
                    
                    messages = []
                    if system_prompt:
                        messages.append(SystemMessage(content=system_prompt))
                    if memory_context:
                        messages.append(SystemMessage(content=f"MEMORY CONTEXT:\n{memory_context}"))
                    messages.append(HumanMessage(content=actual_query))
                    
                    self.logger.debug(f"Sending {len(messages)} messages to agent")
                    self.logger.debug(f"User query: {actual_query}")
                    
                    self.logger.debug("About to call agent.ainvoke() - ENTRY POINT")
                    result = await self.agent.ainvoke({"messages": messages})
                    self.logger.debug("Successfully returned from agent.ainvoke() - EXIT POINT")
                    self.logger.debug(f"Agent result type: {type(result)}")
                    self.logger.debug(f"Agent result: {str(result)[:200]}...")

                    if isinstance(result, dict) and "messages" in result:
                        last_message = result["messages"][-1]
                        msg = getattr(last_message, "content", str(last_message))
                        self.logger.debug(f"Parsed msg {msg}")
                        return msg

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

        def process(self, query: str) -> str:
            """Legacy method - calls primary query() interface."""
            return self.query(query)

        @property
        def tools(self) -> List[Any]:
            """Get the loaded and wrapped tools."""
            return self._tools

        @property
        def is_initialized(self) -> bool:
            """Check if the agent has been initialized."""
            return self._initialized

        # LANGGRAPH COMPATIBILITY
        def invoke(self, state: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """LangGraph compatibility layer - wraps query()."""
            try:
                # Extract user input from LangGraph state format
                if isinstance(state, dict) and "messages" in state:
                    messages = state.get("messages", [])
                    if not messages:
                        from langchain_core.messages import AIMessage
                        return {"messages": [AIMessage(content="No input provided")]}
                    
                    user_input = self._extract_user_input(state)
                    response = self.query(user_input)  # Use primary interface
                    return self._format_langgraph_response(response)
                else:
                    response = self.query(str(state))
                    return self._format_langgraph_response(response)
            except Exception as e:
                from langchain_core.messages import AIMessage
                return {"messages": [AIMessage(content=f"Error processing request: {e}")]}
        
        def _extract_user_input(self, state: Dict[str, Any]) -> str:
            """Extract user input from LangGraph state format."""
            messages = state.get("messages", [])
            if not messages:
                return ""
            
            # Find user input from messages (skip transfer messages)
            for message in messages:
                # Skip transfer-related messages
                if hasattr(message, "content") and "transferred to agent" in str(message.content).lower():
                    continue
                
                if hasattr(message, "content") and hasattr(message, "type"):
                    if message.type in ("human", "user"):
                        return message.content
                elif isinstance(message, dict):
                    content = message.get("content", "")
                    # Skip transfer messages
                    if "transferred to agent" in content.lower():
                        continue
                    role = message.get("role", "")
                    if role in ("user", "human"):
                        return content
            
            # Fallback to last non-transfer message
            for message in reversed(messages):
                if hasattr(message, "content"):
                    content = message.content
                elif isinstance(message, dict):
                    content = message.get("content", "")
                else:
                    content = str(message)
                
                # Skip transfer messages
                if "transferred to agent" not in content.lower():
                    return content
            
            return ""
        
        def _format_langgraph_response(self, response: str) -> Dict[str, Any]:
            """Format response for LangGraph."""
            from langchain_core.messages import AIMessage
            return {"messages": [AIMessage(content=response)]}

    class SubAgentWithMCP(SubAgent):
        """SubAgent implementation with MCP capabilities."""
        
        def __init__(
            self,
            llm: Any,
            mcp_config_path: Union[str, Path],
            memory_session: Optional[Any] = None,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            **kwargs: Any,
        ) -> None:
            """Initialize SubAgentWithMCP.
            
            Args:
                llm: Language model instance (required)
                mcp_config_path: Path to MCP configuration file (required)
                memory_session: Injected memory session (dependency injection)
                name: Optional agent name
                prompt: Optional system prompt
                **kwargs: Additional configuration parameters
            """
            if not mcp_config_path:
                raise ValueError("mcp_config_path is required for SubAgentWithMCP")
            
            # Resolve MCP config path
            resolved_path = self._resolve_mcp_config_path(mcp_config_path)
            
            # Provide default prompt if none specified
            if prompt is None:
                prompt = "You are a helpful AI assistant with MCP tools for enhanced capabilities."
            
            # Initialize with dependency injection
            super().__init__(
                llm=llm,
                memory_session=memory_session,
                mcp_config_path=resolved_path,
                name=name,
                prompt=prompt,
                **kwargs
            )
        
        def _execute_with_llm(self, user_prompt: str, enhanced_input: Dict) -> str:
            """Execute with MCP tools."""
            # Implementation depends on specific MCP agent logic
            return f"MCP agent response to: {user_prompt}"
        
        
        def _resolve_mcp_config_path(self, mcp_config_path: Union[str, Path]) -> Path:
            """Resolve MCP config path relative to the agent's file location."""
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
        """SubAgent implementation without MCP."""
        
        def __init__(
            self,
            llm: Any,
            tools: Optional[List[Any]] = None,
            memory_session: Optional[Any] = None,
            name: Optional[str] = None,
            prompt: Optional[str] = None,
            **kwargs: Any,
        ) -> None:
            """Initialize SubAgentWithoutMCP.
            
            Args:
                llm: Language model instance (required)
                tools: Optional list of external tools
                memory_session: Injected memory session (dependency injection)
                name: Optional agent name
                prompt: Optional system prompt
                **kwargs: Additional configuration parameters
            """
            # Provide default prompt if none specified
            if prompt is None:
                prompt = "You are a helpful AI assistant."
            
            # Initialize without MCP configuration
            super().__init__(
                llm=llm,
                memory_session=memory_session,
                mcp_config_path=None,  # No MCP
                name=name,
                prompt=prompt,
                tools=tools or [],
                **kwargs
            )
        
        def _execute_with_llm(self, user_prompt: str, enhanced_input: Dict) -> str:
            """Execute with direct tools."""
            # Implementation depends on specific non-MCP agent logic
            return f"Non-MCP agent response to: {user_prompt}"
        


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
