"""Clean AgentDK Application Architecture.

This module provides the modern AgentDK architecture with dependency injection.
All deprecated classes have been removed.

Use:
- App (ABC): Pure application base class  
- RootAgent: App + AgentInterface with multiple inheritance
- create_memory_session(): Factory for dependency injection
"""

# Import the clean architecture
from .agent_interface import App, RootAgent, AgentInterface, SubAgent, SubAgentWithMCP, SubAgentWithoutMCP, create_memory_session

# Clean exports - no deprecated classes
__all__ = [
    'App',
    'RootAgent', 
    'AgentInterface',
    'SubAgent',
    'SubAgentWithMCP', 
    'SubAgentWithoutMCP',
    'create_memory_session'
]