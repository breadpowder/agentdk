"""Common utilities for AgentDK applications.

This module provides reusable utility functions for building applications
with AgentDK agents, including response extraction, workflow creation,
and memory context formatting.
"""

from typing import Any, Dict, List
from ..core.logging_config import get_logger


def extract_response(result: Any) -> str:
    """Extract response content from LangGraph result.
    
    This is a common pattern used across different agent applications
    to extract the final response from LangGraph workflow results.
    
    Args:
        result: LangGraph workflow result (can be dict, list, or other formats)
        
    Returns:
        Extracted response string
        
    Examples:
        # Extract from standard LangGraph message format
        result = {"messages": [AIMessage(content="Hello world")]}
        response = extract_response(result)  # "Hello world"
        
        # Handle dict format messages
        result = {"messages": [{"content": "Hello", "role": "assistant"}]}
        response = extract_response(result)  # "Hello"
    """
    logger = get_logger()
    
    # Handle dict with messages (most common LangGraph format)
    if isinstance(result, dict) and 'messages' in result:
        messages = result['messages']
        if messages:
            last_message = messages[-1]
            
            # Extract content from AIMessage or similar objects
            if hasattr(last_message, 'content'):
                return last_message.content
            
            # Extract content from dict format messages
            elif isinstance(last_message, dict) and 'content' in last_message:
                return last_message['content']
            
            # Log warning for unexpected message format
            logger.warning(f"Unexpected message format: {type(last_message)}")
    
    # Handle direct string results
    if isinstance(result, str):
        return result
    
    # Handle list of messages directly
    if isinstance(result, list) and result:
        last_item = result[-1]
        if hasattr(last_item, 'content'):
            return last_item.content
        elif isinstance(last_item, dict) and 'content' in last_item:
            return last_item['content']
    
    # Fallback: return string representation
    logger.warning(f"Using fallback string conversion for result type: {type(result)}")
    return str(result)


def format_memory_context(memory_context: Dict[str, Any]) -> str:
    """Format memory context in a readable way for LLM consumption.
    
    Takes memory context from MemoryManager and formats it into a
    human-readable string that can be included in prompts.
    
    Args:
        memory_context: Memory context dictionary from MemoryManager
        
    Returns:
        Formatted memory context string
        
    Examples:
        memory_context = {
            "recent_conversation": ["Query: tables", "Response: Found 5 tables"],
            "user_preferences": {"format": "table"},
            "relevant_facts": ["User works with financial data"]
        }
        formatted = format_memory_context(memory_context)
    """
    if not memory_context:
        return ""
    
    formatted_parts = []
    
    # Format recent conversation
    if 'recent_conversation' in memory_context:
        recent = memory_context['recent_conversation']
        if recent:
            formatted_parts.append("Recent conversation:")
            for item in recent:
                formatted_parts.append(f"  - {item}")
    
    # Format user preferences
    if 'user_preferences' in memory_context:
        prefs = memory_context['user_preferences']
        if prefs:
            formatted_parts.append("User preferences:")
            for key, value in prefs.items():
                formatted_parts.append(f"  - {key}: {value}")
    
    # Format relevant facts
    if 'relevant_facts' in memory_context:
        facts = memory_context['relevant_facts']
        if facts:
            formatted_parts.append("Relevant context:")
            for fact in facts:
                formatted_parts.append(f"  - {fact}")
    
    # Format working memory
    if 'working_memory' in memory_context:
        working = memory_context['working_memory']
        if working:
            formatted_parts.append("Current session context:")
            if isinstance(working, str):
                formatted_parts.append(f"  - {working}")
            elif isinstance(working, list):
                for item in working:
                    formatted_parts.append(f"  - {item}")
    
    return "\\n".join(formatted_parts)


def create_supervisor_workflow(agents: List[Any], model: Any, prompt: str) -> Any:
    """Create a supervisor workflow with the given agents.
    
    This is a common pattern for creating multi-agent workflows using
    the LangGraph supervisor pattern.
    
    Args:
        agents: List of agent instances to supervise
        model: Language model instance for the supervisor
        prompt: System prompt for the supervisor
        
    Returns:
        Compiled LangGraph workflow
        
    Raises:
        ImportError: If langgraph_supervisor is not available
        Exception: If workflow creation fails
        
    Examples:
        agents = [eda_agent, research_agent]
        workflow = create_supervisor_workflow(agents, llm, supervisor_prompt)
        result = workflow.invoke({"messages": [{"role": "user", "content": "Hello"}]})
    """
    logger = get_logger()
    
    try:
        from langgraph_supervisor import create_supervisor
        
        # Create supervisor workflow
        workflow = create_supervisor(agents, model=model, prompt=prompt)
        app = workflow.compile()
        
        logger.info(f"Created supervisor workflow with {len(agents)} agents")
        return app
        
    except ImportError as e:
        logger.error(f"Missing required dependency: {e}")
        raise ImportError(
            "langgraph_supervisor is required for supervisor workflows. "
            "Install with: pip install langgraph langgraph-supervisor"
        ) from e
    except Exception as e:
        logger.error(f"Failed to create supervisor workflow: {e}")
        raise


def prepare_query_with_memory(query: str, memory_context: Dict[str, Any]) -> str:
    """Prepare a query string with memory context for agent processing.
    
    Formats user query with memory context in a way that preserves
    the original query while providing relevant context to agents.
    
    Args:
        query: Original user query
        memory_context: Memory context from MemoryManager
        
    Returns:
        Formatted query string with memory context
        
    Examples:
        formatted_query = prepare_query_with_memory(
            "Show tables", 
            {"recent_conversation": ["Previously asked about customers"]}
        )
        # Result: "User query: Show tables\\nMemory context: Recent conversation:\\n  - Previously asked about customers"
    """
    if not memory_context:
        return query
    
    formatted_context = format_memory_context(memory_context)
    if formatted_context:
        return f"User query: {query}\\nMemory context: {formatted_context}"
    else:
        return query


def create_workflow_messages(query: str, memory_context: Dict[str, Any] = None) -> List[Dict[str, str]]:
    """Create LangGraph-compatible messages from query and memory context.
    
    Args:
        query: User query string
        memory_context: Optional memory context
        
    Returns:
        List of message dictionaries compatible with LangGraph workflows
    """
    if memory_context:
        formatted_query = prepare_query_with_memory(query, memory_context)
        return [{"role": "user", "content": formatted_query}]
    else:
        return [{"role": "user", "content": query}]