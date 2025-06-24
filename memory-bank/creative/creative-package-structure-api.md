🎨🎨🎨 ENTERING CREATIVE PHASE: PACKAGE STRUCTURE & PUBLIC API DESIGN 🎨🎨🎨

📌 CREATIVE PHASE START: Package Structure & Public API Design
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ PROBLEM
   Description: Design proper package structure for pip distribution and public API patterns
   Requirements:
   - Fix package naming (agentic-media-gen -> agentdk)
   - Pip-ready structure in src/agentdk/
   - Clean public API for agent creation
   - Support target usage pattern from design_doc.md
   - Python 3.11+ compatibility
   - Maintain backward compatibility during transition
   
   Constraints:
   - Must support: EDAAgent(llm=llm, prompt=prompt_defined)
   - Integration with LangGraph supervisor pattern
   - Clean separation between core and examples
   - Easy installation via pip install agentdk

2️⃣ OPTIONS
   Option A: Flat Package Structure - All components at package root level
   Option B: Modular Package Structure - Organized by functionality (core, agent, mcp)
   Option C: Layered Package Structure - Clear separation of public/private APIs

3️⃣ ANALYSIS
   | Criterion | Flat Structure | Modular Structure | Layered Structure |
   |-----|-----|-----|-----|
   | Simplicity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
   | Maintainability | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
   | API Clarity | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
   | Extensibility | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
   | Import Simplicity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
   
   Key Insights:
   - Flat Structure is simplest but doesn't scale well
   - Modular Structure provides good organization
   - Layered Structure offers best API design but requires more planning

4️⃣ DECISION
   Selected: Option C: Layered Package Structure with clear public API
   Rationale: Best long-term approach for a pip-distributed package. Provides clear
   separation between public and private APIs, making it easier for users while
   maintaining internal flexibility.
   
5️⃣ IMPLEMENTATION NOTES
   - Create clear public API in __init__.py with controlled exports
   - Organize internal modules by functionality
   - Fix pyproject.toml package naming and paths
   - Provide simple import patterns for common use cases
   - Maintain examples/ as separate demonstration code

🎨 CREATIVE CHECKPOINT: Package Structure Strategy Selected

## Detailed Package Structure Design

### Target Package Structure
```
src/
└── agentdk/                    # Main package
    ├── __init__.py            # Public API exports
    ├── core/                  # Core utilities (internal)
    │   ├── __init__.py
    │   ├── mcp_load.py       # MCP configuration utilities
    │   └── logging_config.py  # Centralized logging
    ├── agent/                 # Agent interfaces and implementations
    │   ├── __init__.py
    │   ├── agent_interface.py # Base interfaces
    │   └── factory.py         # Agent creation utilities
    ├── mcp/                   # MCP-specific utilities (internal)
    │   ├── __init__.py
    │   ├── client.py         # MCP client wrappers
    │   └── tools.py          # Tool wrapping utilities
    └── exceptions.py          # Package-specific exceptions

examples/                      # Example implementations (not in package)
├── subagent/
│   ├── eda_agent.py          # Simplified EDA agent
│   ├── mcp_config.json       # Example MCP configuration
│   └── eda_system_prompt.py  # System prompt
└── supervisor_example.py      # LangGraph supervisor example
```

### Public API Design (src/agentdk/__init__.py)
```python
"""
AgentDK - Agent Development Kit for LangGraph + MCP Integration

A Python package for building intelligent agents with MCP (Model Context Protocol)
integration and LangGraph orchestration.
"""

from .agent.agent_interface import AgentInterface, SubAgentInterface
from .agent.factory import create_agent, AgentConfig
from .exceptions import AgentDKError, MCPConfigError, AgentInitializationError

# Public API version
__version__ = "0.1.0"

# Controlled public exports
__all__ = [
    # Core interfaces
    "AgentInterface",
    "SubAgentInterface",
    
    # Agent creation
    "create_agent",
    "AgentConfig",
    
    # Exceptions
    "AgentDKError",
    "MCPConfigError", 
    "AgentInitializationError",
]

# Convenience imports for common usage patterns
from .agent.factory import create_eda_agent

# Additional convenience functions
def quick_start():
    """Quick start guide for AgentDK."""
    print("""
    AgentDK Quick Start:
    
    1. Basic agent creation:
       from agentdk import create_agent
       agent = create_agent('eda', llm=your_llm)
    
    2. Custom configuration:
       from agentdk import AgentConfig, create_agent
       config = AgentConfig(mcp_config_path='path/to/config.json')
       agent = create_agent('custom', config=config)
    
    3. LangGraph integration:
       from langgraph.prebuilt import create_supervisor
       workflow = create_supervisor([agent], model=model)
    """)
```

### Agent Factory Pattern
```python
# src/agentdk/agent/factory.py
"""Agent factory for creating configured agents."""

from typing import Optional, Dict, Any, Union
from pathlib import Path
import inspect

from .agent_interface import SubAgentInterface
from ..core.mcp_load import get_mcp_config
from ..exceptions import AgentInitializationError

class AgentConfig:
    """Configuration for agent creation."""
    
    def __init__(
        self,
        mcp_config_path: Optional[Union[str, Path]] = None,
        llm = None,
        system_prompt: Optional[str] = None,
        log_level: str = "INFO",
        **kwargs
    ):
        self.mcp_config_path = Path(mcp_config_path) if mcp_config_path else None
        self.llm = llm
        self.system_prompt = system_prompt
        self.log_level = log_level
        self.extra_config = kwargs

def create_agent(
    agent_type: str,
    config: Optional[AgentConfig] = None,
    llm = None,
    **kwargs
) -> SubAgentInterface:
    """
    Create an agent of the specified type.
    
    Args:
        agent_type: Type of agent to create ('eda', 'custom', etc.)
        config: Agent configuration object
        llm: Language model instance (for backward compatibility)
        **kwargs: Additional configuration parameters
    
    Returns:
        Configured agent instance
    
    Example:
        # Simple usage
        agent = create_agent('eda', llm=my_llm)
        
        # With configuration
        config = AgentConfig(mcp_config_path='my_config.json')
        agent = create_agent('eda', config=config, llm=my_llm)
    """
    if config is None:
        config = AgentConfig(llm=llm, **kwargs)
    elif llm is not None:
        config.llm = llm
    
    # Agent type registry
    agent_types = {
        'eda': _create_eda_agent,
        'custom': _create_custom_agent,
    }
    
    if agent_type not in agent_types:
        raise AgentInitializationError(f"Unknown agent type: {agent_type}")
    
    return agent_types[agent_type](config)

def create_eda_agent(llm = None, prompt: Optional[str] = None, **kwargs) -> SubAgentInterface:
    """
    Create an EDA (Exploratory Data Analysis) agent.
    
    This function provides backward compatibility with the existing usage pattern:
    eda_agent = EDAAgent(llm=llm, prompt=prompt_defined)
    
    Args:
        llm: Language model instance
        prompt: System prompt (optional)
        **kwargs: Additional configuration
    
    Returns:
        Configured EDA agent
    """
    config = AgentConfig(llm=llm, system_prompt=prompt, **kwargs)
    return create_agent('eda', config=config)

def _create_eda_agent(config: AgentConfig) -> SubAgentInterface:
    """Internal function to create EDA agent."""
    # Import here to avoid circular imports
    from examples.subagent.eda_agent import EDAAgent
    
    # Create agent with configuration
    agent = EDAAgent(
        config_dict=config.extra_config,
        model_config=_create_model_config(config.llm),
        log_level=config.log_level
    )
    
    return agent

def _create_custom_agent(config: AgentConfig) -> SubAgentInterface:
    """Internal function to create custom agent."""
    # Placeholder for custom agent creation
    raise NotImplementedError("Custom agent creation not yet implemented")

def _create_model_config(llm):
    """Create model configuration from LLM instance."""
    # This would create appropriate ModelConfig
    # Implementation depends on existing ModelConfig class
    class SimpleModelConfig:
        def __init__(self, llm):
            self.llm = llm
    
    return SimpleModelConfig(llm)
```

### Updated pyproject.toml
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "agentdk"  # CHANGED from agentic-media-gen
version = "0.1.0"
description = "Agent Development Kit for LangGraph + MCP Integration"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"  # CHANGED from >=3.10
authors = [
    {name = "zineng", email = "breadpowder@gmail.com"},
]
keywords = ["ai", "agents", "langraph", "mcp", "agentic"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",  # CHANGED
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

dependencies = [
    "langchain-core>=0.3.63",
    "langchain-mcp-adapters>=0.1.7",
    "langgraph>=0.4.8",
    "nest-asyncio>=1.6.0",
    "mcp[cli]>=1.8.1",
    "pydantic>=2.11.5",
    "python-dotenv>=1.1.0",
    "pyyaml>=6.0.2",
    "sqlparse>=0.4.4",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "pytest-cov>=4.1.0",
    "black>=24.0.0",
    "isort>=5.13.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
    "mysql-connector-python>=8.0.0",  # For testing
]

[project.urls]
Homepage = "https://github.com/zineng/agentdk"
Repository = "https://github.com/zineng/agentdk"
Issues = "https://github.com/zineng/agentdk/issues"

[tool.hatch.version]
path = "src/agentdk/__init__.py"  # CHANGED

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
]

[tool.hatch.build.targets.wheel]
packages = ["src/agentdk"]  # CHANGED

# ... rest of tool configurations remain the same
```

### Usage Examples

#### Basic Usage (Target Pattern from design_doc.md)
```python
# examples/supervisor_example.py
from agentdk import create_eda_agent
from langgraph.prebuilt import create_react_agent, create_supervisor

# Create EDA agent (matches target usage pattern)
eda_agent = create_eda_agent(llm=llm, prompt=prompt_defined)

# Create research agent
def web_search(query: str) -> str:
    return "Search results..."

research_agent = create_react_agent(
    model=model,
    tools=[web_search],
    name="research_expert",
    prompt="You are a world class researcher with access to web search."
)

# Create supervisor workflow
workflow = create_supervisor(
    [research_agent, eda_agent],
    model=model,
    prompt=(
        "You are a team supervisor managing a research expert and an eda_agent. "
        "For current events, use research_agent. "
        "For data exploration, use eda_agent."
    )
)
```

#### Advanced Usage
```python
from agentdk import create_agent, AgentConfig

# Advanced configuration
config = AgentConfig(
    mcp_config_path="custom_mcp_config.json",
    llm=my_llm,
    system_prompt="Custom system prompt",
    log_level="DEBUG"
)

agent = create_agent('eda', config=config)
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 CREATIVE PHASE END: Package Structure & Public API Design

🎨🎨🎨 EXITING CREATIVE PHASE - PACKAGE STRUCTURE & API DECIDED 🎨🎨🎨
