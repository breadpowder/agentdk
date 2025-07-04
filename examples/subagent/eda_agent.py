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
from .prompts import get_eda_agent_prompt


def create_eda_agent(
    llm: Optional[Any] = None,
    mcp_config_path: Optional[Union[str, Path]] = None,
    name: str = "eda_agent",
    **kwargs: Any
) -> Any:
    """Create an EDA (Exploratory Data Analysis) agent using builder pattern.
    
    Args:
        llm: Language model instance
        mcp_config_path: Path to MCP configuration file. If not provided,
                        uses default 'mcp_config.json' in same directory
        name: Agent name for identification
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
        .build())


# Backward compatibility alias - allows existing code to work
EDAAgent = create_eda_agent