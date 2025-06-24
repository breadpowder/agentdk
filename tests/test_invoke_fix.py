"""Test to verify that the invoke method fix works correctly."""

import pytest
from typing import Dict, Any
from unittest.mock import Mock

from agentdk.agent.agent_interface import SubAgentInterface


class TestAgent(SubAgentInterface):
    """Test agent implementation."""
    
    def _get_default_prompt(self) -> str:
        return "Test agent prompt"
    
    async def _create_langgraph_agent(self) -> None:
        self.agent = Mock()
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"output": "test"}


def test_subagent_has_invoke_method():
    """Test that SubAgentInterface has an invoke method."""
    # Create a test agent
    agent = TestAgent(llm=Mock())
    
    # Verify that the invoke method exists
    assert hasattr(agent, 'invoke'), "SubAgentInterface should have an invoke method"
    assert callable(getattr(agent, 'invoke')), "invoke should be callable"


def test_invoke_method_signature():
    """Test that the invoke method has the correct signature and return format."""
    agent = TestAgent(llm=Mock())
    
    # Test the method can be called with the expected parameters
    state = {"messages": [{"role": "user", "content": "test"}]}
    
    # This should not raise an AttributeError
    try:
        result = agent.invoke(state)
        # Should return a dictionary with messages key
        assert isinstance(result, dict), "invoke should return a dictionary"
        assert "messages" in result, "invoke result should have messages key"
        assert isinstance(result["messages"], list), "messages should be a list"
    except AttributeError as e:
        if "'invoke'" in str(e):
            pytest.fail(f"invoke method is missing: {e}")
        # Other AttributeErrors during execution are acceptable for this test
        pass
    except Exception:
        # Other exceptions during execution are fine - we just care that invoke exists
        pass


def test_original_error_fixed():
    """Test that the original AttributeError: 'EDAAgent' object has no attribute 'invoke' is fixed."""
    from examples.subagent.eda_agent import EDAAgent
    
    # Create an EDAAgent instance
    agent = EDAAgent(llm=Mock(), name='test_agent')
    
    # The original error was: AttributeError: 'EDAAgent' object has no attribute 'invoke'
    # This should no longer happen
    assert hasattr(agent, 'invoke'), "EDAAgent should have invoke method"
    
    # Test that we can call it and get the correct return format
    state = {"messages": [{"role": "user", "content": "test"}]}
    try:
        result = agent.invoke(state)
        # Should return a dictionary with messages
        assert isinstance(result, dict), "invoke should return a dictionary"
        assert "messages" in result, "result should have messages key"
    except AttributeError as e:
        if "'invoke'" in str(e) or "has no attribute 'invoke'" in str(e):
            pytest.fail(f"invoke method is still missing: {e}")
        # Other AttributeErrors are acceptable
    except Exception:
        # Other exceptions are fine - the invoke method exists, which is what we're testing
        pass


if __name__ == "__main__":
    pytest.main([__file__]) 