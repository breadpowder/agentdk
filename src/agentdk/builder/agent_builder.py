"""Agent Builder - Fluent API for creating agents without boilerplate classes.

This module provides a builder pattern that eliminates the need for users to define
agent classes by handling all boilerplate generically. Users can create agents by
specifying prompts, LLMs, MCP configs, and tools through a fluent API.
"""

from typing import Any, Dict, Optional, List, Union, Callable
from pathlib import Path
import inspect

from ..agent.agent_interface import SubAgent, SubAgentWithMCP, SubAgentWithoutMCP, create_memory_session
from ..core.logging_config import get_logger


class AgentBuilder:
    """Fluent API builder for creating agents without class definitions."""

    def __init__(self) -> None:
        """Initialize the agent builder."""
        self._config: Dict[str, Any] = {}
        self._logger = get_logger()

    def with_llm(self, llm: Any) -> 'AgentBuilder':
        """Set the language model for the agent.
        
        Args:
            llm: Language model instance (ChatOpenAI, ChatAnthropic, etc.)
            
        Returns:
            Self for method chaining
        """
        self._config['llm'] = llm
        return self

    def with_prompt(self, prompt: Union[str, Callable[[], str], Path]) -> 'AgentBuilder':
        """Set the system prompt for the agent.
        
        Args:
            prompt: System prompt - can be:
                   - string literal: "You are a helpful assistant"
                   - function: get_eda_agent_prompt (will be called)
                   - variable: my_prompt_string
                   - file path: "prompts/analyst.txt"
                   
        Returns:
            Self for method chaining
        """
        self._config['prompt'] = prompt
        return self

    def with_mcp_config(self, config_path: Union[str, Path]) -> 'AgentBuilder':
        """Set MCP configuration path (optional).
        
        Args:
            config_path: Path to MCP configuration JSON file
            
        Returns:
            Self for method chaining
        """
        self._config['mcp_config_path'] = str(config_path)
        return self

    def with_tools(self, tools: List[Any]) -> 'AgentBuilder':
        """Set custom tools for the agent (alternative to MCP).
        
        Args:
            tools: List of tool functions or objects
            
        Returns:
            Self for method chaining
        """
        self._config['tools'] = tools
        return self

    def with_name(self, name: str) -> 'AgentBuilder':
        """Set the agent name.
        
        Args:
            name: Name for the agent (used in logging and identification)
            
        Returns:
            Self for method chaining
        """
        self._config['name'] = name
        return self

    def with_session(self, resume_session: bool = False) -> 'AgentBuilder':
        """Set session management for the agent.
        
        Args:
            resume_session: Whether to resume from previous session
            
        Returns:
            Self for method chaining
        """
        self._config['resume_session'] = resume_session
        return self

    def with_memory(self, enable: bool = True, user_id: str = "default", config: Optional[Dict[str, Any]] = None) -> 'AgentBuilder':
        """Set memory configuration for the agent.
        
        Args:
            enable: Whether to enable memory system (default: True)
            user_id: User identifier for scoped memory (default: "default")
            config: Optional memory configuration dictionary
            
        Returns:
            Self for method chaining
        """
        self._config['enable_memory'] = enable
        self._config['user_id'] = user_id
        self._config['memory_config'] = config
        return self

    def build(self) -> SubAgent:
        """Build the agent using concrete implementation.
        
        Returns:
            Configured agent that implements SubAgent with memory capabilities
            
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Validate required configuration
        if 'llm' not in self._config or self._config['llm'] is None:
            raise ValueError("LLM is required. Use .with_llm(llm) to set it.")

        # Resolve the prompt
        resolved_prompt = self._resolve_prompt()
        self._config['resolved_prompt'] = resolved_prompt

        # Create and return concrete agent
        return self._create_agent()

    def _resolve_prompt(self) -> str:
        """Resolve prompt from various input types.
        
        Returns:
            Resolved prompt string
        """
        prompt_input = self._config.get('prompt')
        
        if prompt_input is None:
            return "You are a helpful AI assistant."

        # Handle callable (function)
        if callable(prompt_input):
            return prompt_input()

        # Handle string/Path
        if isinstance(prompt_input, (str, Path)):
            path_obj = Path(prompt_input)
            # Check if it's a file path that exists
            if path_obj.exists() and path_obj.is_file():
                return path_obj.read_text(encoding='utf-8')
            else:
                # Regular string literal
                return str(prompt_input)

        # Fallback: convert to string
        return str(prompt_input)

    def _create_agent(self) -> SubAgent:
        """Create concrete agent instance with dependency injection.
        
        Returns:
            SubAgentWithMCP or SubAgentWithoutMCP instance
        """
        has_mcp = 'mcp_config_path' in self._config and self._config['mcp_config_path']
        
        # Create memory session using factory (dependency injection)
        memory_session = create_memory_session(
            name=self._config.get('name'),
            user_id=self._config.get('user_id', 'default'),
            enable_memory=self._config.get('enable_memory', True),
            memory_config=self._config.get('memory_config'),
            require_memory=self._config.get('require_memory', False)
        )
        
        # Common parameters for both agent types (clean architecture)
        common_params = {
            'llm': self._config['llm'],
            'memory_session': memory_session,  # Dependency injection
            'name': self._config.get('name'),
            'prompt': self._config.get('resolved_prompt')
        }
        
        if has_mcp:
            # Create SubAgentWithMCP
            return SubAgentWithMCP(
                mcp_config_path=self._config['mcp_config_path'],
                **common_params
            )
        else:
            # Create SubAgentWithoutMCP
            return SubAgentWithoutMCP(
                tools=self._config.get('tools', []),
                **common_params
            )


def buildAgent(
    agent_class: Optional[str] = None,
    llm: Optional[Any] = None,
    memory_session: Optional[Any] = None,
    mcp_config_path: Optional[Union[str, Path]] = None,
    tools: Optional[List[Any]] = None,
    name: Optional[str] = None,
    prompt: Optional[str] = None,
    **kwargs: Any
) -> Union[AgentBuilder, SubAgent]:
    """Create agent using direct function call or fluent API.
    
    This function supports two usage patterns:
    1. Direct creation: buildAgent(agent_class="SubAgentWithMCP", llm=llm, ...)
    2. Fluent API: buildAgent().with_llm(llm).with_prompt(...).build()
    
    Args:
        agent_class: Agent class to create ("SubAgentWithMCP" or "SubAgentWithoutMCP")
        llm: Language model instance
        memory_session: Injected memory session (dependency injection)
        mcp_config_path: Path to MCP configuration
        tools: List of tools for non-MCP agents
        name: Agent name
        prompt: System prompt
        **kwargs: Additional configuration
        
    Returns:
        Agent instance if direct creation, AgentBuilder if fluent API
        
    Examples:
        # Direct creation (new clean way)
        agent = buildAgent(
            agent_class="SubAgentWithMCP",
            llm=llm,
            mcp_config_path="config.json",
            memory_session=memory_session
        )
        
        # Fluent API (backward compatible)
        agent = (buildAgent()
            .with_llm(llm)
            .with_prompt("You are helpful")
            .build())
    """
    # Direct creation pattern (clean new architecture)
    if agent_class is not None:
        if agent_class == "SubAgentWithMCP":
            if not mcp_config_path:
                raise ValueError("mcp_config_path is required for SubAgentWithMCP")
            return SubAgentWithMCP(
                llm=llm,
                mcp_config_path=mcp_config_path,
                memory_session=memory_session,
                name=name,
                prompt=prompt,
                **kwargs
            )
        elif agent_class == "SubAgentWithoutMCP":
            return SubAgentWithoutMCP(
                llm=llm,
                tools=tools or [],
                memory_session=memory_session,
                name=name,
                prompt=prompt,
                **kwargs
            )
        else:
            raise ValueError(f"Unknown agent_class: {agent_class}. Use 'SubAgentWithMCP' or 'SubAgentWithoutMCP'")
    
    # Fluent API pattern (backward compatible)
    return AgentBuilder()