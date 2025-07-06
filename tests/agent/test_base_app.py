"""Tests for agentdk.agent.base_app module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, List

from agentdk.agent.base_app import BaseMemoryApp, SupervisorApp


class ConcreteBaseMemoryApp(BaseMemoryApp):
    """Concrete implementation of BaseMemoryApp for testing."""
    
    def create_workflow(self, model: Any) -> Any:
        """Create a mock workflow for testing."""
        mock_workflow = Mock()
        mock_workflow.invoke.return_value = {
            "messages": [Mock(content="Workflow response")]
        }
        return mock_workflow


class TestBaseMemoryApp:
    """Test the BaseMemoryApp class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_model = Mock()
    
    @patch('agentdk.agent.base_app.MemoryAwareAgent.__init__')
    def test_init_minimal_config(self, mock_super_init):
        """Test BaseMemoryApp initialization with minimal configuration."""
        mock_super_init.return_value = None  # MemoryAwareAgent.__init__ returns None
        
        app = ConcreteBaseMemoryApp(self.mock_model)
        
        # Verify super().__init__ was called with defaults
        mock_super_init.assert_called_once_with(
            memory=True, 
            user_id="default", 
            memory_config=None,
            resume_session=None
        )
        
        assert app.model == self.mock_model
        assert app.app is not None  # Workflow was created
    
    @patch('agentdk.agent.base_app.MemoryAwareAgent.__init__')
    def test_init_custom_config(self, mock_super_init):
        """Test BaseMemoryApp initialization with custom configuration."""
        mock_super_init.return_value = None
        
        memory_config = {"context_tokens": 1024}
        app = ConcreteBaseMemoryApp(
            self.mock_model,
            memory=False,
            user_id="test_user",
            memory_config=memory_config
        )
        
        # Verify super().__init__ was called with custom params
        mock_super_init.assert_called_once_with(
            memory=False,
            user_id="test_user",
            memory_config=memory_config,
            resume_session=None
        )
        
        assert app.model == self.mock_model
    
    @patch('agentdk.agent.base_app.MemoryAwareAgent.__init__')
    def test_call_method_flow(self, mock_super_init):
        """Test the __call__ method processing flow."""
        mock_super_init.return_value = None
        
        app = ConcreteBaseMemoryApp(self.mock_model)
        
        # Mock memory-aware methods
        enhanced_input = {
            'memory_context': {"user_preferences": {"format": "table"}},
            'query': 'test query'
        }
        app.process_with_memory = Mock(return_value=enhanced_input)
        app.finalize_with_memory = Mock(return_value="Final response")
        
        # Mock workflow messages creation
        mock_messages = [{"role": "user", "content": "formatted query"}]
        
        with patch('agentdk.agent.base_app.create_workflow_messages', return_value=mock_messages) as mock_create_messages, \
             patch('agentdk.agent.base_app.extract_response', return_value="Extracted response") as mock_extract:
            
            result = app("test query")
            
            # Verify processing flow
            app.process_with_memory.assert_called_once_with("test query")
            mock_create_messages.assert_called_once_with("test query", {"user_preferences": {"format": "table"}})
            
            # Verify workflow invocation
            expected_input = enhanced_input.copy()
            expected_input['messages'] = mock_messages
            app.app.invoke.assert_called_once_with(expected_input)
            
            # Verify response processing
            mock_extract.assert_called_once()
            app.finalize_with_memory.assert_called_once_with("test query", "Extracted response")
            
            assert result == "Final response"
    
    @patch('agentdk.agent.base_app.MemoryAwareAgent.__init__')
    def test_call_method_no_memory_context(self, mock_super_init):
        """Test __call__ method when no memory context is provided."""
        mock_super_init.return_value = None
        
        app = ConcreteBaseMemoryApp(self.mock_model)
        
        # Mock memory methods returning minimal data
        enhanced_input = {'query': 'test query'}
        app.process_with_memory = Mock(return_value=enhanced_input)
        app.finalize_with_memory = Mock(return_value="Final response")
        
        mock_messages = [{"role": "user", "content": "test query"}]
        
        with patch('agentdk.agent.base_app.create_workflow_messages', return_value=mock_messages) as mock_create_messages, \
             patch('agentdk.agent.base_app.extract_response', return_value="Response"):
            
            result = app("test query")
            
            # Should call create_workflow_messages with None memory context
            mock_create_messages.assert_called_once_with("test query", None)
            
            assert result == "Final response"
    
    @patch('agentdk.agent.base_app.MemoryAwareAgent.__init__')
    def test_workflow_invoke_error_propagation(self, mock_super_init):
        """Test that workflow invocation errors are propagated."""
        mock_super_init.return_value = None
        
        app = ConcreteBaseMemoryApp(self.mock_model)
        app.process_with_memory = Mock(return_value={})
        app.finalize_with_memory = Mock()
        
        # Make workflow raise an error
        app.app.invoke.side_effect = Exception("Workflow error")
        
        with patch('agentdk.agent.base_app.create_workflow_messages', return_value=[]):
            with pytest.raises(Exception, match="Workflow error"):
                app("test query")
    
    def test_abstract_create_workflow_enforcement(self):
        """Test that create_workflow is abstract and must be implemented."""
        
        class IncompleteApp(BaseMemoryApp):
            # Don't implement create_workflow
            pass
        
        # Should not be able to instantiate without implementing create_workflow
        with pytest.raises(TypeError):
            IncompleteApp(self.mock_model)


class TestSupervisorApp:
    """Test the SupervisorApp class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_model = Mock()
        self.agents_config = [
            {"type": "eda", "name": "eda_agent"},
            {"type": "research", "name": "research_agent"}
        ]
    
    @patch('agentdk.agent.base_app.BaseMemoryApp.__init__')
    def test_init_minimal_config(self, mock_super_init):
        """Test SupervisorApp initialization with minimal configuration."""
        mock_super_init.return_value = None
        
        app = SupervisorApp(self.mock_model)
        
        assert app.agents_config == []
        assert app.supervisor_prompt is None
        
        # Verify BaseMemoryApp.__init__ was called with defaults
        mock_super_init.assert_called_once_with(
            self.mock_model,
            resume_session=None
        )
    
    @patch('agentdk.agent.base_app.BaseMemoryApp.__init__')
    def test_init_custom_config(self, mock_super_init):
        """Test SupervisorApp initialization with custom configuration."""
        mock_super_init.return_value = None
        
        custom_prompt = "You are a custom supervisor"
        app = SupervisorApp(
            self.mock_model,
            agents_config=self.agents_config,
            supervisor_prompt=custom_prompt,
            memory=False,
            user_id="test_user"
        )
        
        assert app.agents_config == self.agents_config
        assert app.supervisor_prompt == custom_prompt
        
        # Verify kwargs passed to parent
        mock_super_init.assert_called_once_with(
            self.mock_model,
            memory=False,
            user_id="test_user",
            resume_session=None
        )
    
    @patch('agentdk.agent.base_app.BaseMemoryApp.__init__')
    def test_create_workflow_success(self, mock_super_init):
        """Test successful workflow creation."""
        mock_super_init.return_value = None
        
        # Create app that won't try to create workflow in __init__
        app = SupervisorApp.__new__(SupervisorApp)
        app.agents_config = self.agents_config
        app.supervisor_prompt = "Custom prompt"
        
        # Mock agent creation
        mock_agent1 = Mock()
        mock_agent2 = Mock()
        
        # Mock supervisor workflow creation
        mock_workflow = Mock()
        
        with patch.object(app, '_create_agent_from_config', side_effect=[mock_agent1, mock_agent2]) as mock_create_agent, \
             patch('agentdk.agent.app_utils.create_supervisor_workflow', return_value=mock_workflow) as mock_create_supervisor:
            
            result = app.create_workflow(self.mock_model)
            
            # Verify agent creation
            assert mock_create_agent.call_count == 2
            mock_create_agent.assert_any_call(self.agents_config[0], self.mock_model)
            mock_create_agent.assert_any_call(self.agents_config[1], self.mock_model)
            
            # Verify supervisor creation
            mock_create_supervisor.assert_called_once_with(
                [mock_agent1, mock_agent2],
                self.mock_model,
                "Custom prompt"
            )
            
            assert result == mock_workflow
    
    @patch('agentdk.agent.base_app.BaseMemoryApp.__init__')
    def test_create_workflow_default_prompt(self, mock_super_init):
        """Test workflow creation with default supervisor prompt."""
        mock_super_init.return_value = None
        
        app = SupervisorApp.__new__(SupervisorApp)
        app.agents_config = [{"type": "test"}]
        app.supervisor_prompt = None
        
        mock_agent = Mock()
        mock_workflow = Mock()
        
        with patch.object(app, '_create_agent_from_config', return_value=mock_agent), \
             patch.object(app, '_get_default_supervisor_prompt', return_value="Default prompt") as mock_get_default, \
             patch('agentdk.agent.app_utils.create_supervisor_workflow', return_value=mock_workflow) as mock_create_supervisor:
            
            result = app.create_workflow(self.mock_model)
            
            # Verify default prompt was used
            mock_get_default.assert_called_once()
            mock_create_supervisor.assert_called_once_with(
                [mock_agent],
                self.mock_model,
                "Default prompt"
            )
    
    @patch('agentdk.agent.base_app.BaseMemoryApp.__init__')
    def test_create_workflow_empty_agents(self, mock_super_init):
        """Test workflow creation with empty agents list."""
        mock_super_init.return_value = None
        
        app = SupervisorApp.__new__(SupervisorApp)
        app.agents_config = []
        app.supervisor_prompt = "Test prompt"
        
        mock_workflow = Mock()
        
        with patch('agentdk.agent.app_utils.create_supervisor_workflow', return_value=mock_workflow) as mock_create_supervisor:
            result = app.create_workflow(self.mock_model)
            
            # Should create workflow with empty agents list
            mock_create_supervisor.assert_called_once_with(
                [],
                self.mock_model,
                "Test prompt"
            )
    
    def test_create_agent_from_config_not_implemented(self):
        """Test that _create_agent_from_config raises NotImplementedError."""
        app = SupervisorApp.__new__(SupervisorApp)
        
        with pytest.raises(NotImplementedError) as exc_info:
            app._create_agent_from_config({"type": "test"}, self.mock_model)
        
        assert "Subclasses should override" in str(exc_info.value)
        assert "_create_agent_from_config" in str(exc_info.value)
    
    def test_get_default_supervisor_prompt(self):
        """Test default supervisor prompt content."""
        app = SupervisorApp.__new__(SupervisorApp)
        
        prompt = app._get_default_supervisor_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "supervisor" in prompt.lower()
        assert "agent" in prompt.lower()
        # Should contain guidance about routing and not modifying responses
        assert "route" in prompt.lower() or "appropriate" in prompt.lower()
        assert "unchanged" in prompt.lower() or "not modify" in prompt.lower()


class TestSupervisorAppIntegration:
    """Test SupervisorApp integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_model = Mock()
    
    def test_concrete_supervisor_app_implementation(self):
        """Test a concrete SupervisorApp implementation."""
        
        class ConcreteSupervisorApp(SupervisorApp):
            """Concrete implementation for testing."""
            
            def _create_agent_from_config(self, config: Dict[str, Any], model: Any) -> Any:
                """Create mock agent based on config."""
                mock_agent = Mock()
                mock_agent.name = config.get('name', 'default_agent')
                mock_agent.type = config.get('type', 'generic')
                return mock_agent
        
        agents_config = [
            {"type": "eda", "name": "eda_agent"},
            {"type": "research", "name": "research_agent"}
        ]
        
        mock_workflow = Mock()
        
        with patch('agentdk.agent.base_app.BaseMemoryApp.__init__'), \
             patch('agentdk.agent.app_utils.create_supervisor_workflow', return_value=mock_workflow) as mock_create_supervisor:
            
            app = ConcreteSupervisorApp(
                self.mock_model,
                agents_config=agents_config,
                supervisor_prompt="Test supervisor"
            )
            
            # Manually call create_workflow since __init__ is mocked
            result = app.create_workflow(self.mock_model)
            
            # Verify workflow creation
            mock_create_supervisor.assert_called_once()
            call_args = mock_create_supervisor.call_args
            
            # Check agents were created correctly
            agents = call_args[0][0]
            assert len(agents) == 2
            assert agents[0].name == "eda_agent"
            assert agents[0].type == "eda"
            assert agents[1].name == "research_agent"
            assert agents[1].type == "research"
            
            # Check other parameters
            assert call_args[0][1] == self.mock_model
            assert call_args[0][2] == "Test supervisor"
            
            assert result == mock_workflow
    
    @patch('agentdk.agent.base_app.BaseMemoryApp.__init__')
    def test_supervisor_app_with_memory_integration(self, mock_super_init):
        """Test SupervisorApp integration with memory system."""
        mock_super_init.return_value = None
        
        class TestSupervisorWithMemory(SupervisorApp):
            def _create_agent_from_config(self, config, model):
                return Mock()
        
        memory_config = {"context_tokens": 2048}
        
        app = TestSupervisorWithMemory(
            self.mock_model,
            agents_config=[{"type": "test"}],
            memory=True,
            user_id="memory_user",
            memory_config=memory_config
        )
        
        # Verify memory configuration was passed to parent
        mock_super_init.assert_called_once_with(
            self.mock_model,
            memory=True,
            user_id="memory_user",
            memory_config=memory_config,
            resume_session=None
        )


class TestBaseMemoryAppErrorScenarios:
    """Test error scenarios for BaseMemoryApp."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_model = Mock()
    
    @patch('agentdk.agent.base_app.MemoryAwareAgent.__init__')
    def test_workflow_creation_error(self, mock_super_init):
        """Test error handling during workflow creation."""
        mock_super_init.return_value = None
        
        class FailingWorkflowApp(BaseMemoryApp):
            def create_workflow(self, model):
                raise Exception("Workflow creation failed")
        
        # Should propagate the error
        with pytest.raises(Exception, match="Workflow creation failed"):
            FailingWorkflowApp(self.mock_model)
    
    @patch('agentdk.agent.base_app.MemoryAwareAgent.__init__')
    def test_memory_processing_error(self, mock_super_init):
        """Test error handling in memory processing."""
        mock_super_init.return_value = None
        
        app = ConcreteBaseMemoryApp(self.mock_model)
        app.process_with_memory = Mock(side_effect=Exception("Memory error"))
        
        with pytest.raises(Exception, match="Memory error"):
            app("test query")
    
    @patch('agentdk.agent.base_app.MemoryAwareAgent.__init__')
    def test_response_extraction_error(self, mock_super_init):
        """Test error handling in response extraction."""
        mock_super_init.return_value = None
        
        app = ConcreteBaseMemoryApp(self.mock_model)
        app.process_with_memory = Mock(return_value={})
        app.finalize_with_memory = Mock(return_value="Final")
        
        with patch('agentdk.agent.base_app.create_workflow_messages', return_value=[]), \
             patch('agentdk.agent.base_app.extract_response', side_effect=Exception("Extraction error")):
            
            with pytest.raises(Exception, match="Extraction error"):
                app("test query")


class TestInheritancePatterns:
    """Test inheritance and override patterns."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_model = Mock()
    
    def test_multiple_inheritance_levels(self):
        """Test multiple levels of inheritance."""
        
        class MiddleApp(BaseMemoryApp):
            """Intermediate class with shared functionality."""
            
            def create_workflow(self, model):
                workflow = Mock()
                workflow.specialized = False
                return workflow
            
            def custom_processing(self, data):
                return f"Processed: {data}"
        
        class SpecializedApp(MiddleApp):
            """Specialized implementation."""
            
            def create_workflow(self, model):
                workflow = super().create_workflow(model)
                workflow.specialized = True
                return workflow
        
        with patch('agentdk.agent.base_app.BaseMemoryApp.__init__', return_value=None):
            # Test only the inheritance pattern without full initialization
            app = SpecializedApp.__new__(SpecializedApp)
            
            # Test that it can create specialized workflow
            workflow = app.create_workflow(self.mock_model)
            assert hasattr(workflow, 'specialized')
            assert workflow.specialized is True
            
            # Should inherit middle class functionality
            result = app.custom_processing("test")
            assert result == "Processed: test"
    
    def test_method_override_chain(self):
        """Test method override chain in supervisor app."""
        
        class CustomSupervisorApp(SupervisorApp):
            """Custom supervisor with overridden methods."""
            
            def _create_agent_from_config(self, config, model):
                # Custom agent creation logic
                agent = Mock()
                agent.config = config
                agent.model = model
                agent.custom_field = "custom_value"
                return agent
            
            def _get_default_supervisor_prompt(self):
                return "Custom default supervisor prompt"
        
        with patch('agentdk.agent.base_app.BaseMemoryApp.__init__'), \
             patch('agentdk.agent.app_utils.create_supervisor_workflow') as mock_create:
            
            app = CustomSupervisorApp(
                self.mock_model,
                agents_config=[{"type": "custom"}]
            )
            
            # Manually test workflow creation
            app.create_workflow(self.mock_model)
            
            # Verify custom agent creation was used
            mock_create.assert_called_once()
            agents = mock_create.call_args[0][0]
            assert len(agents) == 1
            assert hasattr(agents[0], 'custom_field')
            assert agents[0].custom_field == "custom_value"
            
            # Verify custom prompt was used
            prompt = mock_create.call_args[0][2]
            assert prompt == "Custom default supervisor prompt"