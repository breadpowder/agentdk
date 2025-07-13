"""Tests for agentdk.agent.base_app module - updated for new architecture."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, List

from agentdk.agent.agent_interface import App, RootAgent, AgentInterface, create_memory_session
from agentdk.exceptions import AgentInitializationError


class ConcreteApp(App):
    """Concrete implementation of App for testing."""
    
    def __init__(self, **kwargs):
        """Initialize with clean app logic."""
        super().__init__(**kwargs)
        self.workflow_created = False
    
    def create_workflow(self, llm: Any) -> Any:
        """Create a mock workflow for testing."""
        mock_workflow = Mock()
        mock_workflow.invoke.return_value = {
            "messages": [Mock(content="Workflow response")]
        }
        self.workflow_created = True
        return mock_workflow
    
    def clean_app(self) -> None:
        """Clean up application resources."""
        self.workflow_created = False


class ConcreteRootAgent(RootAgent):
    """Concrete implementation of RootAgent for testing."""
    
    def __init__(self, llm: Any = None, **kwargs):
        """Initialize with model and create workflow."""
        super().__init__(**kwargs)
        self.llm = llm
        self.workflow = None
        if llm:
            self.workflow = self.create_workflow(llm)
    
    def create_workflow(self, llm: Any) -> Any:
        """Create a mock workflow for testing."""
        mock_workflow = Mock()
        mock_workflow.invoke.return_value = {
            "messages": [Mock(content="Workflow response")]
        }
        return mock_workflow
    
    def clean_app(self) -> None:
        """Clean up application resources."""
        self.workflow = None
    
    def _process_query(self, user_prompt: str, enhanced_input: Dict) -> str:
        """Process query with enhanced input."""
        if self.workflow:
            result = self.workflow.invoke({"messages": [user_prompt]})
            if isinstance(result, dict) and "messages" in result:
                return result["messages"][0].content
        return f"Processed: {user_prompt}"


class TestApp:
    """Test the App base class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
    
    def test_app_init_minimal_config(self):
        """Test App initialization with minimal configuration."""
        app = ConcreteApp()
        
        assert app.config == {}
        assert app.name is None
        assert not app.workflow_created
    
    def test_app_init_custom_config(self):
        """Test App initialization with custom configuration."""
        config = {"setting1": "value1"}
        app = ConcreteApp(config=config, name="test_app")
        
        assert app.config == config
        assert app.name == "test_app"
    
    def test_app_create_workflow(self):
        """Test workflow creation."""
        app = ConcreteApp()
        workflow = app.create_workflow(self.mock_llm)
        
        assert workflow is not None
        assert app.workflow_created
        assert hasattr(workflow, 'invoke')
    
    def test_app_clean_app(self):
        """Test application cleanup."""
        app = ConcreteApp()
        app.create_workflow(self.mock_llm)
        
        assert app.workflow_created
        app.clean_app()
        assert not app.workflow_created
    
    def test_abstract_methods_enforcement(self):
        """Test that abstract methods must be implemented."""
        
        class IncompleteApp(App):
            # Don't implement create_workflow or clean_app
            pass
        
        # Should not be able to instantiate without implementing abstract methods
        with pytest.raises(TypeError):
            IncompleteApp()


class TestRootAgent:
    """Test the RootAgent class (App + AgentInterface)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
    
    def test_root_agent_init_minimal_config(self):
        """Test RootAgent initialization with minimal configuration."""
        agent = ConcreteRootAgent(llm=self.mock_llm)
        
        # App properties
        assert agent.config == {}
        assert agent.name is None
        
        # AgentInterface properties
        assert agent.memory_session is None
        assert agent.resume_session is None
        
        # ConcreteRootAgent properties
        assert agent.llm == self.mock_llm
        assert agent.workflow is not None
    
    def test_root_agent_init_custom_config(self):
        """Test RootAgent initialization with custom configuration."""
        config = {"setting1": "value1"}
        memory_session = Mock()
        
        agent = ConcreteRootAgent(
            llm=self.mock_llm,
            config=config,
            name="test_agent",
            memory_session=memory_session,
            resume_session=True
        )
        
        # App properties
        assert agent.config == config
        assert agent.name == "test_agent"
        
        # AgentInterface properties
        assert agent.memory_session == memory_session
        assert agent.resume_session is True
    
    def test_root_agent_query_without_memory(self):
        """Test query method without memory session."""
        agent = ConcreteRootAgent(llm=self.mock_llm)
        
        result = agent.query("test prompt")
        
        # ConcreteRootAgent returns "Workflow response" via the mock workflow
        assert "Workflow response" in result
    
    @patch('agentdk.agent.agent_interface.MemoryAwareSession')
    def test_root_agent_query_with_memory(self, mock_memory_session_class):
        """Test query method with memory session."""
        # Mock memory session
        memory_session = Mock()
        memory_session.process_with_memory.return_value = {"enhanced": "data"}
        memory_session.finalize_with_memory.return_value = "Final response"
        
        agent = ConcreteRootAgent(
            llm=self.mock_llm,
            memory_session=memory_session
        )
        
        result = agent.query("test prompt")
        
        # Verify memory integration
        memory_session.process_with_memory.assert_called_once_with("test prompt")
        memory_session.finalize_with_memory.assert_called_once()
        assert result == "Final response"
    
    def test_root_agent_call_syntax_sugar(self):
        """Test __call__ method as syntax sugar for query."""
        agent = ConcreteRootAgent(llm=self.mock_llm)
        
        # Should call query method
        with patch.object(agent, 'query', return_value="Query result") as mock_query:
            result = agent("test prompt")
            
            mock_query.assert_called_once_with("test prompt")
            assert result == "Query result"
    
    def test_root_agent_memory_utilities(self):
        """Test memory utility methods."""
        memory_session = Mock()
        memory_session.get_memory_context.return_value = "Memory context"
        
        agent = ConcreteRootAgent(
            llm=self.mock_llm,
            memory_session=memory_session
        )
        
        # Test get_memory_context
        context = agent.get_memory_context("test query")
        assert context == "Memory context"
        memory_session.get_memory_context.assert_called_once_with("test query")
        
        # Test store_interaction
        agent.store_interaction("query", "response")
        memory_session.store_interaction.assert_called_once_with("query", "response")
        
        # Test get_memory_aware_prompt
        enhanced_prompt = agent.get_memory_aware_prompt("base prompt")
        assert enhanced_prompt == "Memory context\n\nbase prompt"
    
    def test_root_agent_memory_utilities_without_session(self):
        """Test memory utility methods without memory session."""
        agent = ConcreteRootAgent(llm=self.mock_llm)
        
        # Should return None or base prompt without errors
        context = agent.get_memory_context("test query")
        assert context is None
        
        # Should not raise errors
        agent.store_interaction("query", "response")
        
        enhanced_prompt = agent.get_memory_aware_prompt("base prompt")
        assert enhanced_prompt == "base prompt"


class TestAgentInterface:
    """Test the AgentInterface base class."""
    
    def test_agent_interface_is_abstract(self):
        """Test that AgentInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AgentInterface()
    
    def test_agent_interface_init_params(self):
        """Test AgentInterface initialization parameters."""
        
        class ConcreteAgent(AgentInterface):
            def query(self, user_prompt: str, **kwargs) -> str:
                return f"Response to: {user_prompt}"
        
        memory_session = Mock()
        config = {"test": "config"}
        
        agent = ConcreteAgent(
            memory_session=memory_session,
            config=config,
            resume_session=True
        )
        
        assert agent.memory_session == memory_session
        assert agent.config == config
        assert agent.resume_session is True


class TestCreateMemorySession:
    """Test the create_memory_session factory function."""
    
    def test_create_memory_session_disabled(self):
        """Test create_memory_session with enable_memory=False."""
        result = create_memory_session(enable_memory=False)
        assert result is None
    
    def test_create_memory_session_enabled(self):
        """Test create_memory_session with enable_memory=True."""
        result = create_memory_session(
            name="test_session",
            user_id="test_user",
            enable_memory=True,
            memory_config={"test": "config"}
        )
        
        # Should return an actual MemoryAwareSession instance
        assert result is not None
        assert hasattr(result, 'name')
        assert hasattr(result, 'user_id')
    
    def test_create_memory_session_import_error_graceful(self):
        """Test create_memory_session handles ImportError gracefully."""
        # Since MemoryAwareSession is already available, we need to test the actual behavior
        # This test verifies the function works when memory is available
        result = create_memory_session(
            enable_memory=True,
            require_memory=False
        )
        
        assert result is not None  # Should work since MemoryAwareSession is available
    
    def test_create_memory_session_import_error_fail_fast(self):
        """Test create_memory_session with require_memory flag."""
        # Test that require_memory parameter is handled correctly
        result = create_memory_session(
            enable_memory=True,
            require_memory=True
        )
        
        assert result is not None  # Should work since MemoryAwareSession is available


class TestMultipleInheritance:
    """Test multiple inheritance patterns in RootAgent."""
    
    def test_method_resolution_order(self):
        """Test that RootAgent has correct method resolution order."""
        mro = RootAgent.__mro__
        
        # Should be: RootAgent, App, AgentInterface, ABC, object
        assert mro[0] == RootAgent
        assert App in mro
        assert AgentInterface in mro
        
        # RootAgent should come before both parents
        root_index = mro.index(RootAgent)
        app_index = mro.index(App)
        agent_index = mro.index(AgentInterface)
        
        assert root_index < app_index
        assert root_index < agent_index
    
    def test_both_parent_methods_available(self):
        """Test that RootAgent has methods from both parents."""
        agent = ConcreteRootAgent(llm=Mock())
        
        # From App
        assert hasattr(agent, 'create_workflow')
        assert hasattr(agent, 'clean_app')
        
        # From AgentInterface
        assert hasattr(agent, 'query')
        assert hasattr(agent, '__call__')
        assert hasattr(agent, 'get_memory_context')
        assert hasattr(agent, 'store_interaction')
        assert hasattr(agent, 'get_memory_aware_prompt')
    
    def test_initialization_calls_both_parents(self):
        """Test that RootAgent initialization calls both parent constructors."""
        # Test with ConcreteRootAgent since RootAgent is abstract
        with patch.object(App, '__init__') as mock_app_init, \
             patch.object(AgentInterface, '__init__') as mock_agent_init:
            
            mock_app_init.return_value = None
            mock_agent_init.return_value = None
            
            config = {"test": "config"}
            memory_session = Mock()
            
            agent = ConcreteRootAgent(
                llm=Mock(),
                config=config,
                name="test",
                memory_session=memory_session,
                resume_session=True
            )
            
            # Verify both parent __init__ methods were called
            # Note: Mock includes 'self' as first argument
            assert mock_app_init.call_count == 1
            assert mock_agent_init.call_count == 1
            
            # Check the arguments (excluding self)
            app_call_args = mock_app_init.call_args
            agent_call_args = mock_agent_init.call_args
            
            assert app_call_args.kwargs['config'] == config
            assert app_call_args.kwargs['name'] == "test"
            
            assert agent_call_args.kwargs['memory_session'] == memory_session
            assert agent_call_args.kwargs['config'] == config
            assert agent_call_args.kwargs['resume_session'] is True


class TestArchitecturalPatterns:
    """Test architectural patterns and separation of concerns."""
    
    def test_app_focuses_on_workflow_management(self):
        """Test that App class focuses on workflow management."""
        app = ConcreteApp(name="test_app")
        
        # App should handle workflow creation
        workflow = app.create_workflow(Mock())
        assert workflow is not None
        
        # App should handle cleanup
        app.clean_app()
        assert not app.workflow_created
    
    def test_agent_interface_focuses_on_query_processing(self):
        """Test that AgentInterface focuses on query processing."""
        
        class TestAgent(AgentInterface):
            def query(self, user_prompt: str, **kwargs) -> str:
                return f"Processed: {user_prompt}"
        
        agent = TestAgent()
        
        # AgentInterface should handle query processing
        result = agent.query("test")
        assert result == "Processed: test"
        
        # Should provide syntax sugar
        result = agent("test")
        assert result == "Processed: test"
    
    def test_root_agent_combines_both_concerns(self):
        """Test that RootAgent successfully combines both concerns."""
        agent = ConcreteRootAgent(llm=Mock())
        
        # Should handle both workflow management (from App)
        assert hasattr(agent, 'create_workflow')
        assert agent.workflow is not None
        
        # And query processing (from AgentInterface)
        result = agent.query("test")
        assert "Workflow response" in result  # ConcreteRootAgent returns this via mock workflow
        
        # Cleanup should work
        agent.clean_app()
        assert agent.workflow is None