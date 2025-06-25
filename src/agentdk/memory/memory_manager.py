"""Memory Manager - Central orchestration of all memory types.

This module provides the MemoryManager class that coordinates Working Memory,
Episodic Memory, and Factual Memory, with configurable LLM context pipeline
for cost control and token management.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory
from .factual_memory import FactualMemory


logger = logging.getLogger(__name__)


class MemoryManager:
    """Central memory orchestrator managing all memory types.
    
    Provides unified interface for Working Memory (session context),
    Episodic Memory (conversation history), and Factual Memory (user preferences).
    Includes configurable LLM context pipeline for cost control.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> None:
        """Initialize the Memory Manager.
        
        Args:
            config: Configuration dictionary (falls back to .env variables)
            user_id: User identifier for scoped memory
            session_id: Session identifier for working memory
        """
        self.config = self._load_config(config)
        self.user_id = user_id
        self.session_id = session_id or self._generate_session_id()
        
        # Initialize memory components
        self.working = WorkingMemory(
            user_id=self.user_id
        )
        
        self.episodic = EpisodicMemory(
            user_id=self.user_id,
            storage_path=self.config.get('episodic_storage_path', '/tmp/memory_data/episodic'),
            compression_threshold=self.config.get('episodic_compression_threshold', 1000)
        )
        
        # Create MemoryConfig with proper storage path for factual memory
        from .base import MemoryConfig
        factual_config = MemoryConfig({
            'storage_path': self.config.get('factual_storage_path', '/tmp/memory_data/agentdk_memory.db')
        })
        
        self.factual = FactualMemory(
            user_id=self.user_id,
            config=factual_config
        )
        
        # Initialize async components
        import asyncio
        asyncio.run(self.working.initialize())
        asyncio.run(self.factual.initialize())
        
        logger.info(f"MemoryManager initialized for user {user_id}, session {self.session_id}")
    
    def _load_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Load configuration from provided dict or .env variables.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            Merged configuration with .env fallbacks
        """
        env_config = {
            'memory_max_context_tokens': int(os.getenv('MEMORY_MAX_CONTEXT_TOKENS', '2048')),
            'memory_context_strategy': os.getenv('MEMORY_CONTEXT_STRATEGY', 'prioritized'),
            'memory_enable_summarization': os.getenv('MEMORY_ENABLE_SUMMARIZATION', 'true').lower() == 'true',
            'memory_summarizer_model': os.getenv('MEMORY_SUMMARIZER_MODEL', 'claude-3-haiku'),
            'working_memory_max_messages': int(os.getenv('WORKING_MEMORY_MAX_MESSAGES', '50')),
            'episodic_compression_threshold': int(os.getenv('EPISODIC_COMPRESSION_THRESHOLD', '1000')),
            'episodic_storage_path': os.getenv('EPISODIC_STORAGE_PATH', '/tmp/memory_data/episodic'),
            'factual_storage_path': os.getenv('FACTUAL_STORAGE_PATH', '/tmp/memory_data/factual')
        }
        
        if config:
            env_config.update(config)
        
        return env_config
    
    def _generate_session_id(self) -> str:
        """Generate a unique session identifier.
        
        Returns:
            Unique session ID string
        """
        import uuid
        return f"session_{uuid.uuid4().hex[:8]}"
    
    def store_interaction(self, user_query: str, agent_response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a user-agent interaction across all memory types.
        
        Args:
            user_query: User's input query
            agent_response: Agent's response
            metadata: Optional metadata about the interaction
        """
        interaction_data = {
            'user_query': user_query,
            'agent_response': agent_response,
            'metadata': metadata or {}
        }
        
        # Store in working memory (session context)
        import asyncio
        user_metadata = {'role': 'user', **(metadata or {})}
        assistant_metadata = {'role': 'assistant', **(metadata or {})}
        asyncio.run(self.working.store(f"User: {user_query}", user_metadata))
        asyncio.run(self.working.store(f"Assistant: {agent_response}", assistant_metadata))
        
        # Store in episodic memory (conversation history)
        self.episodic.store_conversation(user_query, agent_response, metadata)
        
        logger.debug(f"Interaction stored across all memory types")
    
    def get_llm_context(self, user_query: str) -> Dict[str, Any]:
        """Get LLM-ready context with token management and cost control.
        
        This implements the configurable context pipeline:
        1. Retrieve relevant memory from all types
        2. Trim to max tokens based on priority
        3. Optional summarization for cost control
        
        Args:
            user_query: Current user query to get context for
            
        Returns:
            LLM-ready context dictionary with memory information
        """
        # Step 1: Retrieve relevant memory from all types
        context_candidates = self._retrieve_relevant_memory(user_query)
        
        # Step 2: Trim to token budget with priority ordering
        trimmed_context = self._trim_to_token_budget(context_candidates)
        
        # Step 3: Optional summarization
        if self.config['memory_enable_summarization']:
            trimmed_context = self._summarize_context(trimmed_context)
        
        return {
            'memory_context': trimmed_context,
            'context_tokens': self._estimate_tokens(str(trimmed_context)),
            'context_strategy': self.config['memory_context_strategy']
        }
    
    def _retrieve_relevant_memory(self, user_query: str) -> Dict[str, Any]:
        """Retrieve relevant memory from all memory types.
        
        Args:
            user_query: User query to find relevant context for
            
        Returns:
            Dictionary with relevant memory from all types
        """
        import asyncio
        return {
            'factual': asyncio.run(self.factual.retrieve(user_query, limit=5)),
            'working': self.working.get_recent_conversation(),
            'episodic': self.episodic.search_conversations(user_query, limit=5)
        }
    
    def _trim_to_token_budget(self, context_candidates: Dict[str, Any]) -> Dict[str, Any]:
        """Trim context to fit within token budget using priority.
        
        Priority: Factual > Working > Episodic
        
        Args:
            context_candidates: Raw context from all memory types
            
        Returns:
            Trimmed context within token budget
        """
        max_tokens = self.config['memory_max_context_tokens']
        trimmed = {}
        current_tokens = 0
        
        # Priority 1: Factual memory (user preferences)
        factual_tokens = self._estimate_tokens(str(context_candidates.get('factual', {})))
        if current_tokens + factual_tokens <= max_tokens:
            trimmed['factual'] = context_candidates.get('factual', {})
            current_tokens += factual_tokens
        
        # Priority 2: Working memory (current session)
        working_tokens = self._estimate_tokens(str(context_candidates.get('working', {})))
        if current_tokens + working_tokens <= max_tokens:
            trimmed['working'] = context_candidates.get('working', {})
            current_tokens += working_tokens
        
        # Priority 3: Episodic memory (conversation history)
        episodic_data = context_candidates.get('episodic', [])
        episodic_trimmed = []
        for conversation in episodic_data:
            conv_tokens = self._estimate_tokens(str(conversation))
            if current_tokens + conv_tokens <= max_tokens:
                episodic_trimmed.append(conversation)
                current_tokens += conv_tokens
            else:
                break
        
        if episodic_trimmed:
            trimmed['episodic'] = episodic_trimmed
        
        logger.debug(f"Context trimmed to {current_tokens} tokens (max: {max_tokens})")
        return trimmed
    
    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize context using configured summarization model.
        
        Args:
            context: Context to summarize
            
        Returns:
            Summarized context
        """
        # TODO: Implement LLM summarization using mem0ai or configured model
        # For now, return context as-is
        logger.debug("Context summarization not yet implemented")
        return context
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4
    
    def get_relevant_context(self, user_query: str) -> Dict[str, Any]:
        """Get relevant context for a user query (simplified interface).
        
        Args:
            user_query: User's query
            
        Returns:
            Relevant context from all memory types
        """
        return self.get_llm_context(user_query)
    
    # User Preference Management (delegated to FactualMemory)
    def set_preference(self, category: str, key: str, value: Any) -> None:
        """Set a user preference.
        
        Args:
            category: Preference category (ui, agent, system)
            key: Preference key
            value: Preference value
        """
        import asyncio
        asyncio.run(self.factual.set_preference(category, key, value))
    
    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get a user preference.
        
        Args:
            category: Preference category
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value or default
        """
        import asyncio
        return asyncio.run(self.factual.get_preference(category, key, default))
    
    def update_preference(self, category: str, key: str, value: Any) -> None:
        """Update an existing user preference.
        
        Args:
            category: Preference category
            key: Preference key
            value: New preference value
        """
        import asyncio
        asyncio.run(self.factual.set_preference(category, key, value))
    
    def delete_preference(self, category: str, key: str) -> bool:
        """Delete a user preference.
        
        Args:
            category: Preference category
            key: Preference key
            
        Returns:
            True if deleted, False if not found
        """
        import asyncio
        return asyncio.run(self.factual.delete_preference(category, key))
    
    # Memory Statistics and Health
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics.
        
        Returns:
            Dictionary with statistics from all memory types
        """
        import asyncio
        return {
            'working': asyncio.run(self.working.get_stats()),
            'episodic': self.episodic.get_stats(),
            'factual': asyncio.run(self.factual.get_stats()),
            'config': {
                'max_context_tokens': self.config['memory_max_context_tokens'],
                'summarization_enabled': self.config['memory_enable_summarization'],
                'context_strategy': self.config['memory_context_strategy']
            }
        }
    
    def clear_memory(self, memory_type: str = "working") -> bool:
        """Clear specified memory type.
        
        Args:
            memory_type: Type to clear (working, episodic, factual, all)
            
        Returns:
            True if successful
        """
        import asyncio
        if memory_type == "working":
            return asyncio.run(self.working.clear(confirm=True))
        elif memory_type == "episodic":
            return self.episodic.clear()
        elif memory_type == "factual":
            return asyncio.run(self.factual.clear(confirm=True))
        elif memory_type == "all":
            return (
                asyncio.run(self.working.clear(confirm=True)) and
                self.episodic.clear() and
                asyncio.run(self.factual.clear(confirm=True))
            )
        else:
            logger.error(f"Unknown memory type: {memory_type}")
            return False 