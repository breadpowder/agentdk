"""Clean agent factory for AgentDK.

This module provides factory functions using the new dependency injection architecture.
"""

from typing import Optional, Dict, Any, Union
from pathlib import Path

from .agent_interface import SubAgentWithMCP, SubAgentWithoutMCP, create_memory_session
from ..core.logging_config import get_logger
from ..exceptions import AgentInitializationError


def create_agent(
    agent_type: str,
    llm: Any,
    mcp_config_path: Optional[Union[str, Path]] = None,
    tools: Optional[list] = None,
    memory_session: Optional[Any] = None,
    name: Optional[str] = None,
    prompt: Optional[str] = None,
    **kwargs: Any
) -> Union[SubAgentWithMCP, SubAgentWithoutMCP]:
    """Create an agent using the clean architecture.
    
    Args:
        agent_type: Type of agent ('mcp' or 'tools')
        llm: Language model instance (required)
        mcp_config_path: Path to MCP configuration (for 'mcp' type)
        tools: List of tools (for 'tools' type)
        memory_session: Injected memory session (dependency injection)
        name: Agent name
        prompt: System prompt
        **kwargs: Additional configuration
    
    Returns:
        Configured agent instance
    
    Examples:
        # MCP agent
        agent = create_agent('mcp', llm=my_llm, mcp_config_path='config.json')
        
        # Tools agent
        agent = create_agent('tools', llm=my_llm, tools=[web_search])
    """
    logger = get_logger()
    
    try:
        # Create memory session if not provided
        if memory_session is None:
            memory_session = create_memory_session(name=name)
        
        if agent_type == 'mcp':
            if not mcp_config_path:
                raise ValueError("mcp_config_path is required for MCP agents")
            
            agent = SubAgentWithMCP(
                llm=llm,
                mcp_config_path=mcp_config_path,
                memory_session=memory_session,
                name=name,
                prompt=prompt,
                **kwargs
            )
            
        elif agent_type == 'tools':
            agent = SubAgentWithoutMCP(
                llm=llm,
                tools=tools or [],
                memory_session=memory_session,
                name=name,
                prompt=prompt,
                **kwargs
            )
            
        else:
            raise ValueError(f"Unknown agent_type: {agent_type}. Use 'mcp' or 'tools'")
        
        logger.info(f"Created {agent_type} agent successfully")
        return agent
        
    except Exception as e:
        raise AgentInitializationError(
            f"Failed to create {agent_type} agent: {e}",
            agent_type=agent_type
        ) from e