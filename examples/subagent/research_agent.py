"""Research Agent factory using AgentDK Builder Pattern.

This module provides a simple factory function to create Research agents using the new
builder pattern, eliminating the need for class definitions and boilerplate code.
"""

import sys
from pathlib import Path
from typing import Any, Optional, List, Dict

# Add src to path for agentdk imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from agentdk.builder.agent_builder import buildAgent

# Handle imports for both CLI and direct usage
try:
    from .prompts import get_research_agent_prompt
except ImportError:
    # Fallback for CLI usage - import from same directory
    import os
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from prompts import get_research_agent_prompt


def create_research_agent(
    llm: Any,
    tools: Optional[List[Any]] = None,
    memory_session: Optional[Any] = None,
    name: str = "research_expert",
    enable_memory: bool = True,
    user_id: str = "default",
    memory_config: Optional[Dict[str, Any]] = None,
    require_memory: bool = False,
    **kwargs: Any
) -> Any:
    """Create a Research agent using dependency injection.
    
    Args:
        llm: Language model instance (required)
        tools: List of research tools (web search, etc.). If not provided, uses empty list
        memory_session: Injected memory session (dependency injection)
        name: Agent name for identification
        enable_memory: Whether to enable memory (used if memory_session is None)
        user_id: User identifier for scoped memory
        memory_config: Optional memory configuration dictionary
        require_memory: If True, fails fast when memory unavailable
        **kwargs: Additional configuration passed to builder
        
    Returns:
        Configured Research agent ready for research tasks
        
    Examples:
        # Basic usage
        research_agent = create_research_agent(llm=my_llm)
        
        # With custom tools
        research_agent = create_research_agent(
            llm=my_llm,
            tools=[web_search_tool, api_tool]
        )
        
        # Use with supervisor
        workflow = create_supervisor([research_agent], model=llm)
    """
    # Set default tools if not provided
    if tools is None:
        tools = []
    
    # Create memory session if needed (dependency injection)
    if memory_session is None and enable_memory:
        from agentdk.agent.agent_interface import create_memory_session
        memory_session = create_memory_session(
            name=name,
            user_id=user_id,
            enable_memory=enable_memory,
            memory_config=memory_config,
            require_memory=require_memory
        )
    
    # Create agent using clean direct interface
    return buildAgent(
        agent_class="SubAgentWithoutMCP",
        llm=llm,
        tools=tools,
        memory_session=memory_session,
        name=name,
        prompt=get_research_agent_prompt(),
        **kwargs
    )