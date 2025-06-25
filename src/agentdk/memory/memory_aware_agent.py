"""Memory-aware agent interface for AgentDK.

This module provides a reusable interface for agents that need memory integration,
including conversation continuity, user preference support, and memory investigation tooling.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
import os

from .memory_manager import MemoryManager
from .memory_tools import MemoryTools


class MemoryAwareAgent(ABC):
    """Abstract base class for agents with memory integration.
    
    Provides conversation continuity, user preference support,
    and memory investigation tooling for any agent implementation.
    
    This class handles all memory-related functionality, allowing
    concrete agent implementations to focus on their core logic
    while gaining memory capabilities.
    """

    def __init__(
        self, 
        memory: bool = True,
        user_id: str = "default",
        memory_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize MemoryAwareAgent with optional memory integration.
        
        Args:
            memory: Whether to enable memory system
            user_id: User identifier for scoped memory
            memory_config: Optional memory configuration
        """
        self.user_id = user_id
        
        # Initialize memory system if available and requested
        self.memory = None
        self.memory_tools = None
        
        if memory:
            try:
                self.memory = MemoryManager(
                    config=memory_config,
                    user_id=user_id
                )
                self.memory_tools = MemoryTools(self.memory)
                print(f"✅ Memory system initialized for user {user_id}")
            except Exception as e:
                print(f"⚠️  Memory initialization failed: {e}")
                print("   Continuing without memory...")
    
    def memory_tool(self, command: str) -> str:
        """Memory investigation tool interface.
        
        Args:
            command: CLI-style memory command
            
        Returns:
            Formatted response from memory tools
        """
        if not self.memory_tools:
            return "❌ Memory system not available"
        
        return self.memory_tools.execute(command)
    
    def get_memory_context(self, query: str) -> Optional[str]:
        """Get memory context for a query.
        
        Args:
            query: User's input query
            
        Returns:
            Memory context string or None if not available
        """
        if not self.memory:
            return None
        
        try:
            return self.memory.get_llm_context(query)
        except Exception as e:
            print(f"⚠️  Memory context retrieval failed: {e}")
            return None
    
    def store_interaction(self, query: str, response: str) -> None:
        """Store an interaction in memory.
        
        Args:
            query: User's input query
            response: Agent's response
        """
        if not self.memory:
            return
        
        try:
            self.memory.store_interaction(query, response)
        except Exception as e:
            print(f"⚠️  Memory storage failed: {e}")
    
    def get_memory_aware_prompt(self, base_prompt: str) -> str:
        """Enhance a base prompt with memory awareness.
        
        Args:
            base_prompt: The agent's base prompt
            
        Returns:
            Enhanced prompt with memory awareness
        """
        if not self.memory:
            return base_prompt
        
        memory_enhancement = """

MEMORY AWARENESS:
- You have access to conversation history and user preferences via memory_context
- Use memory context to understand user preferences (e.g., preferred response format)
- Reference previous conversations when relevant
- Maintain conversation continuity across sessions

USER PREFERENCE SUPPORT:
- Check memory_context for user preferences like response_format
- If user prefers "table" format, ensure responses are formatted accordingly
- Respect user's established preferences from previous interactions"""
        
        return base_prompt + memory_enhancement
    
    def process_with_memory(self, query: str) -> Dict[str, Any]:
        """Process a query with memory enhancement.
        
        This method prepares the input with memory context and handles
        memory storage after processing. Concrete implementations should
        call this method and use the enhanced input.
        
        Args:
            query: User's input query
            
        Returns:
            Dictionary with enhanced input and memory context
        """
        # Get memory context if available
        memory_context = self.get_memory_context(query)
        
        # Prepare enhanced input with memory context
        enhanced_input = {"messages": [{"role": "user", "content": query}]}
        if memory_context:
            enhanced_input["memory_context"] = memory_context
        
        return enhanced_input
    
    def finalize_with_memory(self, query: str, response: str) -> str:
        """Finalize processing by storing interaction in memory.
        
        Args:
            query: Original user query
            response: Agent's response
            
        Returns:
            The response (unchanged)
        """
        # Store interaction in memory
        self.store_interaction(query, response)
        return response
    
    # User preference management methods
    def set_preference(self, category: str, key: str, value: Any) -> str:
        """Set a user preference.
        
        Args:
            category: Preference category (ui, agent, system)
            key: Preference key
            value: Preference value
            
        Returns:
            Status message
        """
        if not self.memory:
            return "❌ Memory system not available"
        
        try:
            self.memory.set_preference(category, key, value)
            return f"✅ Preference set: {category}.{key} = {value}"
        except Exception as e:
            return f"❌ Failed to set preference: {e}"
    
    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get a user preference.
        
        Args:
            category: Preference category
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value or default
        """
        if not self.memory:
            return default
        
        try:
            return self.memory.get_preference(category, key, default)
        except Exception as e:
            print(f"⚠️  Failed to get preference: {e}")
            return default
    
    def get_memory_stats(self) -> str:
        """Get formatted memory statistics.
        
        Returns:
            Formatted memory statistics
        """
        if not self.memory_tools:
            return "❌ Memory system not available"
        
        return self.memory_tools.execute("stats --detailed")
    
    def _format_memory_context(self, memory_context: dict) -> str:
        """Format memory context in a readable way for LLM.
        
        Args:
            memory_context: Raw memory context dictionary
            
        Returns:
            Formatted memory context string
        """
        if not memory_context or 'memory_context' not in memory_context:
            return "No recent conversation history"
        
        context_data = memory_context['memory_context']
        formatted_lines = []
        
        # Format working memory (recent conversation)
        working_memory = context_data.get('working', [])
        if working_memory:
            formatted_lines.append("Recent conversation:")
            for item in working_memory[-3:]:  # Last 3 items
                content = item.get('content', '')
                if content.startswith('User:'):
                    formatted_lines.append(f"  {content}")
                elif content.startswith('Assistant:'):
                    formatted_lines.append(f"  {content}")
        
        # Format factual memory (user preferences)
        factual_memory = context_data.get('factual', [])
        if factual_memory:
            formatted_lines.append("User preferences:")
            for item in factual_memory:
                content = item.get('content', '')
                formatted_lines.append(f"  - {content}")
        
        return "\n".join(formatted_lines) if formatted_lines else "No relevant context available"
    
    @abstractmethod
    def __call__(self, query: str) -> str:
        """Process a query and return a response.
        
        Concrete implementations should:
        1. Call process_with_memory(query) to get enhanced input
        2. Process the query with their specific logic
        3. Call finalize_with_memory(query, response) to store interaction
        4. Return the response
        
        Args:
            query: User's input query
            
        Returns:
            Agent's response
        """
        pass
    
    @abstractmethod
    def create_workflow(self, *args, **kwargs) -> Any:
        """Create the agent's workflow.
        
        Concrete implementations should create their specific workflow
        and can use get_memory_aware_prompt() to enhance their prompts.
        
        Returns:
            Agent's workflow object
        """
        pass 