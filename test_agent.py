"""Simple test agent for CLI validation."""

import sys
from pathlib import Path

# Add src to path for agentdk imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from agentdk import Agent


def get_test_prompt():
    """Simple test prompt."""
    return "You are a helpful test agent. Respond to user queries in a friendly manner."


def create_test_agent(llm=None, **kwargs):
    """Create a simple test agent.
    
    Args:
        llm: Language model instance (optional for testing)
        **kwargs: Additional configuration
        
    Returns:
        Configured test agent
    """
    # Create a mock LLM for testing if none provided
    if llm is None:
        class MockLLM:
            def invoke(self, input_text):
                return {"output": f"Mock response to: {input_text}"}
            
            def __call__(self, input_text):
                return f"Mock response to: {input_text}"
        
        llm = MockLLM()
    
    return (Agent()
        .with_llm(llm)
        .with_prompt(get_test_prompt)
        .with_name("test_agent")
        .build())


# Direct agent instance for testing
root_agent = create_test_agent()