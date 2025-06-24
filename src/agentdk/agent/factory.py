"""Agent factory for creating configured agents with AgentDK.

This module provides factory functions and configuration classes for easy agent creation,
supporting the target usage pattern from design_doc.md while maintaining backward compatibility.
"""

from typing import Optional, Dict, Any, Union, Type
from pathlib import Path
import inspect

from .agent_interface import SubAgentInterface
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
) -> SubAgentInterface:
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


def create_eda_agent(
    llm: Optional[Any] = None,
    prompt: Optional[str] = None,
    mcp_config_path: Optional[Union[str, Path]] = None,
    **kwargs: Any
) -> SubAgentInterface:
    """Create an EDA (Exploratory Data Analysis) agent.
    
    This function provides backward compatibility with the target usage pattern:
    eda_agent = EDAAgent(llm=llm, prompt=prompt_defined)
    
    Args:
        llm: Language model instance
        prompt: System prompt for the agent (alias for system_prompt)
        mcp_config_path: Path to MCP configuration file
        **kwargs: Additional configuration parameters
    
    Returns:
        Configured EDA agent instance
    
    Examples:
        # Target usage pattern from design_doc.md
        eda_agent = create_eda_agent(llm=llm, prompt=prompt_defined)
        
        # With MCP configuration
        eda_agent = create_eda_agent(
            llm=llm, 
            prompt=prompt_defined,
            mcp_config_path='examples/subagent/mcp_config.json'
        )
    """
    # Create configuration with backward compatibility mapping
    config = AgentConfig(
        llm=llm,
        system_prompt=prompt,  # Map 'prompt' to 'system_prompt'
        mcp_config_path=mcp_config_path,
        **kwargs
    )
    
    return create_agent('eda', config=config)


def _get_agent_class(agent_type: str) -> Type[SubAgentInterface]:
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
        'eda': _get_eda_agent_class,
        'custom': _get_custom_agent_class,
    }
    
    if agent_type not in agent_registry:
        supported_types = list(agent_registry.keys())
        raise AgentInitializationError(
            f"Unsupported agent type '{agent_type}'. Supported types: {supported_types}",
            agent_type=agent_type
        )
    
    return agent_registry[agent_type]()


def _get_eda_agent_class() -> Type[SubAgentInterface]:
    """Get the EDA agent class.
    
    Returns:
        EDA agent class
        
    Raises:
        AgentInitializationError: If EDA agent cannot be imported
    """
    try:
        # Import EDA agent from examples (dynamic import to avoid circular dependencies)
        import importlib.util
        import sys
        from pathlib import Path
        
        # Try to import from examples directory
        examples_path = Path("examples/subagent/eda_agent.py")
        if examples_path.exists():
            spec = importlib.util.spec_from_file_location("eda_agent", examples_path)
            if spec and spec.loader:
                eda_module = importlib.util.module_from_spec(spec)
                sys.modules["eda_agent"] = eda_module
                spec.loader.exec_module(eda_module)
                
                # Look for EDA agent class
                for name in dir(eda_module):
                    obj = getattr(eda_module, name)
                    if (inspect.isclass(obj) and 
                        issubclass(obj, SubAgentInterface) and 
                        obj != SubAgentInterface):
                        return obj
        
        # Fallback: create a basic EDA agent class
        return _create_basic_eda_agent_class()
        
    except Exception as e:
        raise AgentInitializationError(
            f"Failed to load EDA agent class: {e}",
            agent_type="eda"
        ) from e


def _get_custom_agent_class() -> Type[SubAgentInterface]:
    """Get a custom agent class.
    
    Returns:
        Custom agent class (basic implementation)
    """
    return _create_basic_agent_class("CustomAgent")


def _create_basic_eda_agent_class() -> Type[SubAgentInterface]:
    """Create a basic EDA agent class as fallback.
    
    Returns:
        Basic EDA agent class
    """
    class BasicEDAAgent(SubAgentInterface):
        """Basic EDA agent implementation."""
        
        def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
            # Extract parameters for SubAgentInterface
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
            """Process a user query for EDA tasks."""
            return f"EDA analysis for: {user_prompt}"
        
        def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
            """Process state for LangGraph integration."""
            # Basic state processing for EDA tasks
            user_input = state.get('user_input', '')
            
            # Perform EDA analysis (placeholder)
            analysis_result = self.query(user_input)
            
            # Update state
            state['eda_analysis'] = analysis_result
            state['agent_output'] = analysis_result
            
            return state
    
    return BasicEDAAgent


def _create_basic_agent_class(class_name: str) -> Type[SubAgentInterface]:
    """Create a basic agent class with the given name.
    
    Args:
        class_name: Name for the agent class
        
    Returns:
        Basic agent class
    """
    class BasicAgent(SubAgentInterface):
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
    agent_class: Type[SubAgentInterface], 
    config: AgentConfig
) -> SubAgentInterface:
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