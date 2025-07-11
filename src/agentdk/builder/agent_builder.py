"""Agent Builder - Fluent API for creating agents without boilerplate classes.

This module provides a builder pattern that eliminates the need for users to define
agent classes by handling all boilerplate generically. Users can create agents by
specifying prompts, LLMs, MCP configs, and tools through a fluent API.
"""

from typing import Any, Dict, Optional, List, Union, Callable
from pathlib import Path
import inspect

from ..agent.agent_interface import SubAgent
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
        self._config['memory_user_id'] = user_id
        self._config['memory_config'] = config
        return self

    def build(self) -> SubAgent:
        """Build the agent using generic implementation.
        
        Returns:
            Configured agent that implements SubAgent with memory capabilities
            
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Validate required configuration
        if 'llm' not in self._config or self._config['llm'] is None:
            raise ValueError("LLM is required. Use .with_llm(llm) to set it.")

        # Validate that either tools or MCP config is provided for functional agent
        has_tools = 'tools' in self._config and self._config['tools']
        has_mcp = 'mcp_config_path' in self._config and self._config['mcp_config_path']
        
        if not has_tools and not has_mcp:
            self._logger.warning(
                "No tools or MCP configuration provided. Agent will have limited functionality."
            )

        # Resolve the prompt
        resolved_prompt = self._resolve_prompt()

        # Create and return generic agent
        return self._create_generic_agent(resolved_prompt)

    def _resolve_prompt(self) -> str:
        """Resolve prompt from various input types.
        
        Returns:
            Resolved prompt string
            
        Raises:
            ValueError: If prompt cannot be resolved
        """
        prompt_input = self._config.get('prompt')
        
        if prompt_input is None:
            return "You are a helpful AI assistant."

        # Handle callable (function)
        if callable(prompt_input):
            try:
                return prompt_input()
            except Exception as e:
                raise ValueError(f"Failed to call prompt function: {e}")

        # Handle string
        if isinstance(prompt_input, str):
            # Check if it's a file path
            if prompt_input.endswith(('.txt', '.md')) and Path(prompt_input).exists():
                try:
                    return Path(prompt_input).read_text(encoding='utf-8')
                except Exception as e:
                    raise ValueError(f"Failed to read prompt file {prompt_input}: {e}")
            else:
                # Regular string literal
                return prompt_input

        # Handle Path object
        if isinstance(prompt_input, Path):
            try:
                return prompt_input.read_text(encoding='utf-8')
            except Exception as e:
                raise ValueError(f"Failed to read prompt file {prompt_input}: {e}")

        # Fallback: convert to string
        return str(prompt_input)

    def _create_generic_agent(self, resolved_prompt: str) -> SubAgent:
        """Create a generic agent that implements all required abstract methods.
        
        Args:
            resolved_prompt: The resolved system prompt string
            
        Returns:
            Generic agent instance with memory capabilities
        """
        config = self._config.copy()
        config['resolved_prompt'] = resolved_prompt

        class GenericAgent(SubAgent):
            """Generic agent implementation that handles all boilerplate."""

            def __init__(self, builder_config: Dict[str, Any]):
                """Initialize generic agent with builder configuration."""
                # Extract parameters for SubAgent (now memory-aware)
                init_kwargs = {
                    'llm': builder_config.get('llm'),
                    'prompt': builder_config.get('resolved_prompt'),
                    'name': builder_config.get('name', 'generic_agent'),
                    'tools': builder_config.get('tools', []),
                    'enable_memory': builder_config.get('enable_memory', True),
                    'resume_session': builder_config.get('resume_session'),
                    'user_id': builder_config.get('memory_user_id', 'default'),
                    'memory_config': builder_config.get('memory_config')
                }
                
                # Add MCP config if provided
                if 'mcp_config_path' in builder_config:
                    init_kwargs['mcp_config_path'] = builder_config['mcp_config_path']
                
                super().__init__(**init_kwargs)
                self._builder_config = builder_config

            def _get_default_prompt(self) -> str:
                """Return the resolved prompt from builder."""
                return self._builder_config['resolved_prompt']

            def __call__(self, query: str) -> str:
                """Process a query and return a response."""
                # Use memory-aware processing from parent class
                enhanced_input = self.process_with_memory(query)
                
                # Simple processing - just return a basic response
                # In a real implementation, this would use the LangGraph agent
                agent_name = self._builder_config.get('name', 'agent')
                
                # Basic response with memory context if available
                memory_context = enhanced_input.get('memory_context')
                if memory_context:
                    result = f"Hello! I'm {agent_name}. I have access to our conversation history and will use it to provide better responses. You asked: {query}"
                else:
                    result = f"Hello! I'm {agent_name}. You asked: {query}"
                
                # Finalize with memory
                return self.finalize_with_memory(query, result)

            def create_workflow(self):
                """Create simple workflow for generic agent."""
                # Return None for simple agents, workflow creation happens in _create_langgraph_agent
                return None

            async def _create_langgraph_agent(self) -> None:
                """Create LangGraph reactive agent with available tools."""
                try:
                    from langgraph.prebuilt import create_react_agent
                    
                    # Create react agent with LLM and tools
                    self.agent = create_react_agent(self.llm, self._tools)
                    
                    self.logger.debug(f"Created LangGraph agent with {len(self._tools)} tools")
                    
                except ImportError as e:
                    self.logger.error(f"Failed to import LangGraph: {e}")
                    raise
                except Exception as e:
                    self.logger.error(f"Failed to create LangGraph agent: {e}")
                    raise

            def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
                """Generic state processing for LangGraph workflows."""
                try:
                    # Extract user input from state
                    user_input = state.get('user_input', state.get('query', ''))
                    
                    if not user_input:
                        self.logger.warning("No user input found in state")
                        state['agent_output'] = "No user input provided"
                        return state

                    # Process the query using inherited method
                    result = self.query(user_input)
                    
                    # Update state with results
                    state['agent_output'] = result
                    state['agent_type'] = self._builder_config.get('name', 'generic')
                    
                    self.logger.info("Agent processing completed successfully")
                    return state

                except Exception as e:
                    error_msg = f"Agent processing error: {e}"
                    self.logger.error(error_msg)
                    
                    state['agent_output'] = error_msg
                    state['error'] = str(e)
                    
                    return state

        return GenericAgent(config)


def Agent() -> AgentBuilder:
    """Factory function to create a new AgentBuilder.
    
    Returns:
        New AgentBuilder instance for fluent API usage
        
    Examples:
        # Basic agent
        agent = (Agent()
            .with_llm(llm)
            .with_prompt("You are helpful")
            .build())
        
        # EDA agent with MCP
        eda_agent = (Agent()
            .with_llm(llm) 
            .with_prompt(get_eda_agent_prompt)
            .with_mcp_config("config.json")
            .with_name("eda_agent")
            .build())
    """
    return AgentBuilder()