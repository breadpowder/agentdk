"""Research Agent factory using AgentDK Builder Pattern.

This module provides a simple factory function to create Research agents using the new
builder pattern, eliminating the need for class definitions and boilerplate code.
"""

import sys
from pathlib import Path
from typing import Any, Optional, List

# Add src to path for agentdk imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from agentdk import Agent

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
    llm: Optional[Any] = None,
    tools: Optional[List[Any]] = None,
    name: str = "research_expert",
    **kwargs: Any
) -> Any:
    """Create a Research agent using builder pattern.
    
    Args:
        llm: Language model instance
        tools: List of research tools (web search, etc.). If not provided, uses empty list
        name: Agent name for identification
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
    
    # Create agent using builder pattern
    return (Agent()
        .with_llm(llm)
        .with_prompt(get_research_agent_prompt)  # Function from prompts.py
        .with_tools(tools)
        .with_name(name)
        .build())


# Backward compatibility alias - allows existing code to work
ResearchAgent = create_research_agent


# Additional backward compatibility function
def create_research_agent_legacy(llm: Any = None, log_level: str = "INFO") -> Any:
    """Create a Research agent instance (legacy compatibility).
    
    Args:
        llm: Language model instance
        log_level: Logging level (ignored - handled by AgentDK core)
        
    Returns:
        Configured Research agent
    """
    return create_research_agent(llm=llm)