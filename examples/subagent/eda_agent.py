"""EDA Agent factory using AgentDK Builder Pattern.

This module provides a simple factory function to create EDA agents using the new
builder pattern, eliminating the need for class definitions and boilerplate code.
"""

import sys
from pathlib import Path
from typing import Any, Optional, Union, Dict

# Add src to path for agentdk imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from agentdk.builder.agent_builder import buildAgent

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
    llm: Any,
    mcp_config_path: Optional[Union[str, Path]] = None,
    memory_session: Optional[Any] = None,
    name: str = "eda_agent",
    enable_memory: bool = True,
    user_id: str = "default",
    memory_config: Optional[Dict[str, Any]] = None,
    require_memory: bool = False,
    **kwargs: Any
) -> Any:
    """Create an EDA (Exploratory Data Analysis) agent using dependency injection.
    
    Args:
        llm: Language model instance (required)
        mcp_config_path: Path to MCP configuration file. If not provided,
                        uses default 'mcp_config.json' in same directory
        memory_session: Injected memory session (dependency injection)
        name: Agent name for identification
        enable_memory: Whether to enable memory (used if memory_session is None)
        user_id: User identifier for scoped memory
        memory_config: Optional memory configuration dictionary
        require_memory: If True, fails fast when memory unavailable
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
        agent_class="SubAgentWithMCP",
        llm=llm,
        mcp_config_path=mcp_config_path,
        memory_session=memory_session,
        name=name,
        prompt=get_eda_agent_prompt(),
        **kwargs
    )