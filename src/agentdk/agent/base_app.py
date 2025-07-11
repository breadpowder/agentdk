"""Base application class for memory-aware AgentDK applications.

This module provides a reusable base class that handles common patterns
for building applications with AgentDK agents, including memory integration,
workflow management, and response processing.
"""

from abc import abstractmethod
from typing import Any, Optional, Dict, List
from ..memory import MemoryAwareAgent
from .app_utils import extract_response, create_workflow_messages


class BaseMemoryApp(MemoryAwareAgent):
    """Base class for memory-aware agent applications.
    
    This class provides common functionality for applications that use
    AgentDK agents with memory integration and LangGraph workflows.
    
    Subclasses only need to implement create_workflow() to define
    their specific agent configuration and workflow logic.
    """

    def __init__(
        self, 
        llm: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        prompt: Optional[str] = None,
        enable_memory: bool = True,
        resume_session: Optional[bool] = None,
        # Backward compatibility parameters
        memory: Optional[bool] = None,
        user_id: str = "default",
        memory_config: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ):
        """Initialize BaseMemoryApp with unified parameters and memory integration.
        
        Args:
            llm: Language model instance
            config: Agent configuration dictionary
            name: Agent name for identification
            prompt: System prompt for the agent
            enable_memory: Whether to enable memory system (default: True)
            resume_session: Whether to resume from previous session (None = no session management)
            memory: [DEPRECATED] Use enable_memory instead
            user_id: User identifier for scoped memory
            memory_config: Optional memory configuration
            **kwargs: Additional configuration parameters
        """
        # Initialize memory system with unified parameters
        super().__init__(
            llm=llm,
            config=config,
            name=name,
            prompt=prompt,
            enable_memory=enable_memory,
            resume_session=resume_session,
            memory=memory,
            user_id=user_id,
            memory_config=memory_config,
            **kwargs
        )
        
        # Note: Workflow creation is now handled by subclasses in their __init__
    
    def __call__(self, query: str) -> str:
        """Process a query with memory-enhanced workflow.
        
        This method handles the common pattern of:
        1. Processing input with memory
        2. Formatting for workflow
        3. Invoking workflow
        4. Extracting response
        5. Finalizing with memory
        
        Args:
            query: User's input query
            
        Returns:
            Agent's response
        """
        # Use memory-aware processing
        enhanced_input = self.process_with_memory(query)
        
        # Create workflow-compatible messages
        memory_context = enhanced_input.get('memory_context')
        messages = create_workflow_messages(query, memory_context)
        enhanced_input['messages'] = messages
        
        # Process with workflow
        result = self.app.invoke(enhanced_input)
        
        # Extract response using common utility
        response = extract_response(result)
        
        # Finalize with memory
        return self.finalize_with_memory(query, response)
    
    @abstractmethod
    def create_workflow(self, model: Any) -> Any:
        """Create the application's workflow.
        
        Subclasses must implement this method to define their specific
        agent configuration and workflow logic.
        
        Args:
            model: Language model instance
            
        Returns:
            Compiled LangGraph workflow
            
        Examples:
            def create_workflow(self, model):
                eda_agent = create_eda_agent(llm=model)
                research_agent = create_research_agent(llm=model)
                return create_supervisor_workflow([eda_agent, research_agent], model, prompt)
        """
        pass


class SupervisorApp(BaseMemoryApp):
    """Specialized base class for supervisor-based multi-agent applications.
    
    This class provides additional utilities specifically for applications
    that use the supervisor pattern with multiple agents.
    """

    def __init__(
        self, 
        llm: Any,
        agents_config: List[Dict[str, Any]] = None,
        supervisor_prompt: str = None,
        enable_memory: bool = True,
        resume_session: Optional[bool] = None,
        # Backward compatibility parameters
        model: Optional[Any] = None,
        **kwargs
    ):
        """Initialize SupervisorApp with unified parameters and agent configuration.
        
        Args:
            llm: Language model instance
            agents_config: List of agent configurations
            supervisor_prompt: Custom supervisor prompt
            enable_memory: Whether to enable memory system (default: True)
            resume_session: Whether to resume from previous session (None = no session management)
            model: [DEPRECATED] Use llm instead
            **kwargs: Additional arguments passed to BaseMemoryApp
        """
        # Handle backward compatibility for model parameter
        if model is not None:
            llm = model
        
        self.agents_config = agents_config or []
        self.supervisor_prompt = supervisor_prompt
        
        super().__init__(
            llm=llm,
            prompt=supervisor_prompt,
            enable_memory=enable_memory,
            resume_session=resume_session,
            **kwargs
        )
    
    def create_workflow(self, model: Any) -> Any:
        """Create supervisor workflow with configured agents.
        
        This default implementation can be overridden by subclasses
        that need custom agent creation logic.
        
        Args:
            model: Language model instance
            
        Returns:
            Compiled supervisor workflow
        """
        from .app_utils import create_supervisor_workflow
        
        # Create agents from configuration
        agents = []
        for agent_config in self.agents_config:
            agent = self._create_agent_from_config(agent_config, model)
            agents.append(agent)
        
        # Get supervisor prompt
        prompt = self.supervisor_prompt or self._get_default_supervisor_prompt()
        
        # Create supervisor workflow
        return create_supervisor_workflow(agents, model, prompt)
    
    def _create_agent_from_config(self, config: Dict[str, Any], model: Any) -> Any:
        """Create an agent from configuration.
        
        This is a helper method that can be overridden by subclasses
        to customize agent creation logic.
        
        Args:
            config: Agent configuration dictionary
            model: Language model instance
            
        Returns:
            Configured agent instance
        """
        # This is a basic implementation - subclasses should override
        # for specific agent creation logic
        agent_type = config.get('type', 'generic')
        
        # This is a basic implementation - real applications should override
        # this method with their specific agent creation logic
        raise NotImplementedError(
            "Subclasses should override _create_agent_from_config() "
            "with their specific agent creation logic"
        )
    
    def _get_default_supervisor_prompt(self) -> str:
        """Get default supervisor prompt.
        
        Returns:
            Default supervisor prompt string
        """
        return """You are a team supervisor managing multiple agents.
        
        Route user queries to the most appropriate agent based on the query content.
        When an agent provides a response, return their complete response unchanged.
        
        Do not modify, summarize, or paraphrase agent responses."""