"""AgentDK Memory System - Multi-level memory management for AI agents.

This module provides a comprehensive memory system with three types of memory:
- Working Memory: Short-term session-aware context (high accuracy)
- Episodic Memory: Long-term conversation history (balanced storage)
- Factual Memory: Persistent user preferences and settings (mutable)

The memory system includes:
- MemoryManager: Central orchestrator for all memory types
- MemoryTools: Investigation and debugging tooling
- Configurable LLM context pipeline for cost control

Example:
    Basic usage:
    >>> from agentdk.memory import MemoryManager, MemoryTools
    >>> memory = MemoryManager()
    >>> memory.set_preference("ui", "response_format", "table")
    
    Investigation tooling:
    >>> tools = MemoryTools(memory)
    >>> tools.execute("show --type factual")
    >>> tools.execute("preferences --list")
    
    Agent integration:
    >>> from agentdk.memory import MemoryManager
    >>> memory = MemoryManager(user_id="user123")
    >>> context = memory.get_llm_context("What are my preferences?")
"""

from .memory_manager import MemoryManager
from .memory_tools import MemoryTools
from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory
from .factual_memory import FactualMemory
from .memory_aware_agent import MemoryAwareAgent

__version__ = "0.1.0"
__all__ = [
    'MemoryManager',
    'MemoryTools', 
    'WorkingMemory',
    'EpisodicMemory',
    'FactualMemory',
    'MemoryAwareAgent'
]
