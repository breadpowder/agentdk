"""Unit tests for CLI agent loading functionality."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from agentdk.cli.agent_loader import AgentLoader


class TestAgentLoader:
    """Test cases for AgentLoader class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.loader = AgentLoader()
    
    def test_agent_loader_initialization(self):
        """Test AgentLoader initializes correctly."""
        assert self.loader is not None
        assert hasattr(self.loader, '_llm_providers')
        assert 'openai' in self.loader._llm_providers
        assert 'anthropic' in self.loader._llm_providers
    
    def test_create_mock_llm(self):
        """Test mock LLM creation."""
        mock_llm = self.loader._create_mock_llm()
        
        # Test invoke method
        result = mock_llm.invoke({"input": "test"})
        assert isinstance(result, dict)
        assert "output" in result
        assert "Mock response to: test" in result["output"]
        
        # Test call method
        result = mock_llm("hello")
        assert "Mock response to: hello" in result
        
        # Test bind method
        bound_llm = mock_llm.bind(temperature=0.5)
        assert bound_llm is mock_llm
    
    def test_load_agent_invalid_path(self):
        """Test loading agent with invalid path."""
        with pytest.raises(ValueError, match="Invalid agent path"):
            self.loader.load_agent(Path("/nonexistent/path"))
    
    def test_load_agent_non_python_file(self):
        """Test loading agent with non-Python file."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as temp_file:
            temp_path = Path(temp_file.name)
            with pytest.raises(ValueError, match="Agent file must be a Python file"):
                self.loader.load_agent(temp_path)
    
    def test_discover_agent_factory_function(self):
        """Test discovering factory functions in module."""
        # Create a mock module with factory function
        mock_module = Mock()
        mock_module.__dict__ = {
            'create_test_agent': Mock(return_value="agent_instance"),
            'some_other_function': Mock(),
            'create_another_agent': Mock(return_value="another_agent")
        }
        
        # Mock dir() to return the attributes
        with patch('builtins.dir', return_value=list(mock_module.__dict__.keys())):
            result = self.loader._discover_agent_in_module(mock_module, None)
            
            # Should find and call the first factory function
            assert result == "agent_instance"
            mock_module.__dict__['create_test_agent'].assert_called_once()
    
    def test_discover_agent_direct_instance(self):
        """Test discovering direct agent instances in module."""
        # Create a mock module with agent instance
        mock_agent = Mock()
        # Add __call__ as a real attribute instead of using del
        mock_agent.__call__ = Mock()
        
        mock_module = Mock()
        mock_module.__dict__ = {
            'root_agent': mock_agent,
            'some_function': Mock()
        }
        
        def custom_hasattr(obj, attr):
            if obj == mock_agent and attr in ['__call__', 'invoke']:
                return True
            return hasattr(obj, attr)
        
        with patch('builtins.dir', return_value=list(mock_module.__dict__.keys())):
            with patch('builtins.hasattr', side_effect=custom_hasattr):
                result = self.loader._discover_agent_in_module(mock_module, None)
                assert result == mock_agent
    
    def test_discover_agent_no_agent_found(self):
        """Test when no agent is found in module."""
        mock_module = Mock()
        mock_module.__dict__ = {
            'some_function': Mock(),
            'some_variable': "value"
        }
        
        def custom_hasattr(obj, attr):
            # For testing, return False for agent-like attributes
            if attr in ['__call__', 'invoke']:
                return False
            return hasattr(obj, attr)
        
        with patch('builtins.dir', return_value=list(mock_module.__dict__.keys())):
            with patch('builtins.hasattr', side_effect=custom_hasattr):
                result = self.loader._discover_agent_in_module(mock_module, None)
                assert result is None


class TestAgentLoaderIntegration:
    """Integration tests for AgentLoader with real files."""
    
    def test_load_simple_agent_file(self):
        """Test loading a simple agent file."""
        # Create a temporary agent file
        agent_code = '''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

def create_test_agent(llm=None, **kwargs):
    class SimpleAgent:
        def __init__(self, llm=None):
            self.llm = llm
            self.name = "simple_agent"
        
        def invoke(self, input_data):
            return {"output": f"Response to: {input_data}"}
        
        def __call__(self, input_text):
            return f"Response to: {input_text}"
    
    return SimpleAgent(llm)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(agent_code)
            temp_file.flush()
            
            try:
                loader = AgentLoader()
                agent_path = Path(temp_file.name)
                
                # Test loading without LLM (should use mock)
                agent = loader.load_agent(agent_path)
                assert agent is not None
                assert hasattr(agent, 'name')
                assert agent.name == "simple_agent"
                
            finally:
                os.unlink(temp_file.name)
    
    @patch('agentdk.cli.agent_loader.click.echo')
    def test_load_agent_with_llm_requirement(self, mock_echo):
        """Test loading agent that requires LLM."""
        agent_code = '''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

def create_test_agent(llm=None, **kwargs):
    if llm is None:
        raise Exception("LLM is required. Use .with_llm(llm) to set it.")
    
    class LLMAgent:
        def __init__(self, llm):
            self.llm = llm
            self.name = "llm_agent"
        
        def invoke(self, input_data):
            return {"output": f"LLM response to: {input_data}"}
    
    return LLMAgent(llm)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(agent_code)
            temp_file.flush()
            
            try:
                loader = AgentLoader()
                agent_path = Path(temp_file.name)
                
                # Test loading - should fallback to mock LLM
                agent = loader.load_agent(agent_path)
                assert agent is not None
                assert hasattr(agent, 'name')
                assert agent.name == "llm_agent"
                
                # Verify mock LLM message was shown
                mock_echo.assert_called()
                echo_calls = [call.args[0] for call in mock_echo.call_args_list]
                assert any("using mock LLM for testing" in call.lower() for call in echo_calls)
                
            finally:
                os.unlink(temp_file.name)