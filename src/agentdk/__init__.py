"""
AgentDK - Agent Development Kit for LangGraph + MCP Integration

A Python package for building intelligent agents with MCP (Model Context Protocol)
integration and LangGraph orchestration.

Examples:
    Basic agent creation:
        from agentdk import create_agent
        agent = create_agent('eda', llm=your_llm)
    
    Custom configuration:
        from agentdk import AgentConfig, create_agent
        config = AgentConfig(mcp_config_path='path/to/config.json')
        agent = create_agent('custom', config=config)
    
"""

from .agent.agent_interface import AgentInterface, SubAgent
from .agent.root_agent import RootAgent, SupervisorAgent
from .agent.factory import create_agent, AgentConfig
from .builder.agent_builder import Agent
from .exceptions import AgentDKError, MCPConfigError, AgentInitializationError

# Public API version
__version__ = "0.1.0"

# Controlled public exports
__all__ = [
    # Core interfaces
    "AgentInterface",
    "SubAgent",
    "RootAgent",
    "SupervisorAgent",
    
    # Agent creation
    "Agent",  # New builder pattern factory
    "create_agent",
    "AgentConfig",
    
    # Exceptions
    "AgentDKError",
    "MCPConfigError", 
    "AgentInitializationError",
    
    # Utilities
    "quick_start",
]


def quick_start() -> None:
    """Display quick start guide for AgentDK."""
    print("""
    🚀 AgentDK Quick Start Guide
    ═══════════════════════════════════════════════════════════════════
    
    📦 Installation:
        pip install agentdk
    
    🔧 Basic Usage:
        from agentdk import create_agent
        agent = create_agent('eda', llm=your_llm)
    
    ⚙️  Custom Configuration:
        from agentdk import AgentConfig, create_agent
        config = AgentConfig(mcp_config_path='path/to/config.json')
        agent = create_agent('custom', config=config, llm=your_llm)
    
    
    🚀 LangGraph Integration:
        from langgraph.prebuilt import create_supervisor
        workflow = create_supervisor([agent], model=model)
    
    📚 More Examples:
        Check the examples/ directory in the AgentDK repository
        https://github.com/zineng/agentdk/tree/main/examples
    
    ═══════════════════════════════════════════════════════════════════
    """)


# Initialize logging on import
from .core.logging_config import ensure_nest_asyncio
ensure_nest_asyncio() 