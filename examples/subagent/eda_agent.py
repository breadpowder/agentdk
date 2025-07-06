"""EDA Agent factory using AgentDK Builder Pattern.

This module provides a simple factory function to create EDA agents using the new
builder pattern, eliminating the need for class definitions and boilerplate code.
"""

import sys
from pathlib import Path
from typing import Any, Optional, Union

# Add src to path for agentdk imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from agentdk import Agent

# Handle imports for both CLI and direct usage
try:
    from .prompts import get_eda_agent_prompt
except ImportError:
    # Fallback for CLI usage - import from same directory
    import os
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from prompts import get_eda_agent_prompt


def create_eda_agent(
    llm: Optional[Any] = None,
    mcp_config_path: Optional[Union[str, Path]] = None,
    name: str = "eda_agent",
    resume_session: bool = False,
    is_parent_agent: bool = False,
    **kwargs: Any
) -> Any:
    """Create an EDA (Exploratory Data Analysis) agent using builder pattern.
    
    Args:
        llm: Language model instance
        mcp_config_path: Path to MCP configuration file. If not provided,
                        uses default 'mcp_config.json' in same directory
        name: Agent name for identification
        resume_session: Whether to resume from previous session (default: False)
        is_parent_agent: Whether this agent manages sessions (default: False for child agents)
        **kwargs: Additional configuration passed to builder
        
    Returns:
        Configured EDA agent ready for data analysis tasks
        
    Examples:
        # Basic usage
        eda_agent = create_eda_agent(llm=my_llm)
        
        # With custom MCP config
        eda_agent = create_eda_agent(
            llm=my_llm,
            mcp_config_path="custom_config.json"
        )
        
        # Use with supervisor
        workflow = create_supervisor([eda_agent], model=llm)
    """
    # Set default MCP config path if not provided
    if mcp_config_path is None:
        mcp_config_path = str(Path(__file__).parent / 'mcp_config.json')
    
    # Create agent using builder pattern
    return (Agent()
        .with_llm(llm)
        .with_prompt(get_eda_agent_prompt)  # Function from prompts.py
        .with_mcp_config(mcp_config_path)
        .with_name(name)
        .with_session(resume_session=resume_session, is_parent_agent=is_parent_agent)
        .build())


# Backward compatibility alias - allows existing code to work
EDAAgent = create_eda_agent