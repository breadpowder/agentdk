"""Agent factory for creating configured agents with AgentDK.

This module provides factory functions and configuration classes for easy agent creation,
supporting the target usage pattern from design_doc.md while maintaining backward compatibility.
"""

from typing import Optional, Dict, Any, Union, Type
from pathlib import Path
import inspect

from .agent_interface import SubAgent
from ..core.logging_config import get_logger
from ..exceptions import AgentInitializationError


class AgentConfig:
    """Configuration for agent creation."""

    def __init__(
        self,
        mcp_config_path: Optional[Union[str, Path]] = None,
        llm: Optional[Any] = None,
        system_prompt: Optional[str] = None,
        log_level: str = "INFO",
        **kwargs: Any
    ) -> None:
        """Initialize agent configuration.
        
        Args:
            mcp_config_path: Path to MCP configuration file
            llm: Language model instance
            system_prompt: System prompt for the agent
            log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
            **kwargs: Additional configuration parameters
        """
        self.mcp_config_path = Path(mcp_config_path) if mcp_config_path else None
        self.llm = llm
        self.system_prompt = system_prompt
        self.log_level = log_level
        self.extra_config = kwargs


def create_agent(
    agent_type: str,
    config: Optional[AgentConfig] = None,
    llm: Optional[Any] = None,
    **kwargs: Any
) -> SubAgent:
    """Create an agent of the specified type.
    
    Args:
        agent_type: Type of agent to create ('eda', 'custom', etc.)
        config: Agent configuration object
        llm: Language model instance (for backward compatibility)
        **kwargs: Additional configuration parameters
    
    Returns:
        Configured agent instance
    
    Raises:
        AgentInitializationError: If agent creation fails
    
    Examples:
        # Simple usage
        agent = create_agent('eda', llm=my_llm)
        
        # With configuration
        config = AgentConfig(mcp_config_path='my_config.json')
        agent = create_agent('eda', config=config, llm=my_llm)
        
        # With inline configuration
        agent = create_agent('eda', llm=my_llm, mcp_config_path='config.json')
    """
    logger = get_logger()
    
    try:
        # Merge configuration sources
        if config is None:
            config = AgentConfig(llm=llm, **kwargs)
        elif llm is not None:
            config.llm = llm
        
        # Update config with additional kwargs
        for key, value in kwargs.items():
            if not hasattr(config, key):
                config.extra_config[key] = value
            else:
                setattr(config, key, value)
        
        # Get agent class
        agent_class = _get_agent_class(agent_type)
        
        # Create agent instance
        agent = _instantiate_agent(agent_class, config)
        
        logger.info(f"Created {agent_type} agent successfully")
        return agent
        
    except Exception as e:
        raise AgentInitializationError(
            f"Failed to create {agent_type} agent: {e}",
            agent_type=agent_type
        ) from e




def _get_agent_class(agent_type: str) -> Type[SubAgent]:
    """Get the agent class for the specified type.
    
    Args:
        agent_type: Type of agent to create
        
    Returns:
        Agent class
        
    Raises:
        AgentInitializationError: If agent type is not supported
    """
    # Registry of supported agent types
    agent_registry = {
        'custom': _get_custom_agent_class,
    }
    
    if agent_type not in agent_registry:
        supported_types = list(agent_registry.keys())
        raise AgentInitializationError(
            f"Unsupported agent type '{agent_type}'. Supported types: {supported_types}",
            agent_type=agent_type
        )
    
    return agent_registry[agent_type]()




def _get_custom_agent_class() -> Type[SubAgent]:
    """Get a custom agent class.
    
    Returns:
        Custom agent class (basic implementation)
    """
    return _create_basic_agent_class("CustomAgent")




def _create_basic_agent_class(class_name: str) -> Type[SubAgent]:
    """Create a basic agent class with the given name.
    
    Args:
        class_name: Name for the agent class
        
    Returns:
        Basic agent class
    """
    class BasicAgent(SubAgent):
        """Basic agent implementation."""
        
        def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
            mcp_config_path = None
            if config:
                mcp_config_path = config.mcp_config_path
            
            super().__init__(
                config=config.extra_config if config else kwargs,
                mcp_config_path=mcp_config_path,
                **kwargs
            )
            
            self._config = config
        
        def query(self, user_prompt: str, **kwargs: Any) -> str:
            """Process a user query."""
            return f"Agent response for: {user_prompt}"
        
        def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
            """Process state for LangGraph integration."""
            user_input = state.get('user_input', '')
            result = self.query(user_input)
            
            state['agent_output'] = result
            return state
    
    # Dynamically set class name
    BasicAgent.__name__ = class_name
    BasicAgent.__qualname__ = class_name
    
    return BasicAgent


def _instantiate_agent(
    agent_class: Type[SubAgent], 
    config: AgentConfig
) -> SubAgent:
    """Instantiate an agent with the given configuration.
    
    Args:
        agent_class: Agent class to instantiate
        config: Configuration for the agent
        
    Returns:
        Agent instance
    """
    try:
        # Prepare constructor arguments
        constructor_args = {
            'config': config,
        }
        
        # Add any additional arguments that the agent class expects
        constructor_signature = inspect.signature(agent_class.__init__)
        
        # Map config attributes to constructor parameters
        for param_name in constructor_signature.parameters:
            if param_name in ['self', 'config']:
                continue
                
            if hasattr(config, param_name):
                constructor_args[param_name] = getattr(config, param_name)
            elif param_name in config.extra_config:
                constructor_args[param_name] = config.extra_config[param_name]
        
        # Create agent instance
        agent = agent_class(**constructor_args)
        
        return agent
        
    except Exception as e:
        raise AgentInitializationError(
            f"Failed to instantiate agent {agent_class.__name__}: {e}",
            agent_type=agent_class.__name__
        ) from e 