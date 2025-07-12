"""Root Agent - Reusable base class for supervisor and multi-agent patterns.

This module provides a standardized base class for creating supervisor agents
and other root-level agents that coordinate multiple subagents or complex workflows.
"""

from abc import abstractmethod
from typing import Any, Optional, Dict, List
from ..memory import MemoryAwareAgent


class RootAgent(MemoryAwareAgent):
    """Reusable base class for supervisor agents and multi-agent coordinators.
    
    This class provides a foundation for agents that manage other agents,
    coordinate complex workflows, or serve as the main entry point for
    multi-agent applications.
    
    Features:
    - Memory integration with enable_memory flag support
    - Unified initialization API
    - Abstract workflow creation pattern
    - Standard response processing
    - Session management
    
    Usage:
        class MySupervisorAgent(RootAgent):
            def create_workflow(self):
                # Create your workflow with subagents
                return workflow
    """

    def __init__(
        self,
        llm: Any,
        config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        prompt: Optional[str] = None,
        enable_memory: bool = True,
        resume_session: Optional[bool] = None,
        **kwargs: Any
    ):
        """Initialize RootAgent with unified parameters.
        
        Args:
            llm: Language model instance (required)
            config: Agent configuration dictionary
            name: Agent name for identification
            prompt: System prompt for the agent
            enable_memory: Whether to enable memory system (default: True)
            resume_session: Whether to resume from previous session (None = no session management)
            **kwargs: Additional configuration parameters
        """
        super().__init__(
            llm=llm,
            config=config,
            name=name or "root_agent",
            prompt=prompt,
            enable_memory=enable_memory,
            resume_session=resume_session,
            **kwargs
        )
        
        # Store the workflow after creation
        self.workflow: Optional[Any] = None
        
        # Initialize workflow in subclass
        self.workflow = self.create_workflow()

    @abstractmethod
    def create_workflow(self) -> Any:
        """Create the agent's workflow.
        
        Subclasses must implement this method to define their specific
        workflow logic, which may include subagent coordination,
        supervisor patterns, or complex processing pipelines.
        
        Returns:
            Compiled workflow object (e.g., LangGraph workflow)
            
        Examples:
            def create_workflow(self):
                eda_agent = create_eda_agent(llm=self.llm)
                research_agent = create_research_agent(llm=self.llm)
                return create_supervisor_workflow([eda_agent, research_agent], self.llm, self.prompt)
        """
        pass

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
        if not self.workflow:
            return "Error: Workflow not initialized"
        
        # Use memory-aware processing
        enhanced_input = self.process_with_memory(query)
        
        # Create workflow-compatible messages
        memory_context = enhanced_input.get('memory_context')
        messages = self._create_workflow_messages(query, memory_context)
        enhanced_input['messages'] = messages
        
        # Process with workflow
        result = self.workflow.invoke(enhanced_input)
        
        # Extract response
        response = self._extract_response(result)
        
        # Finalize with memory
        return self.finalize_with_memory(query, response)

    def _create_workflow_messages(self, query: str, memory_context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Create workflow-compatible message format.
        
        Args:
            query: User's input query
            memory_context: Optional memory context
            
        Returns:
            List of messages in workflow format
        """
        messages = []
        
        # Add system message with memory context if available
        system_prompt = self._get_default_prompt()
        if memory_context:
            system_prompt += f"\n\nMEMORY CONTEXT:\n{memory_context}"
        
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": query})
        
        return messages

    def _extract_response(self, result: Any) -> str:
        """Extract response from workflow result.
        
        Args:
            result: Workflow execution result
            
        Returns:
            Extracted response string
        """
        # Handle different result formats
        if isinstance(result, dict):
            # LangGraph result format
            if "messages" in result:
                messages = result["messages"]
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, "content"):
                        return last_message.content
                    elif isinstance(last_message, dict):
                        return last_message.get("content", str(last_message))
                    else:
                        return str(last_message)
            
            # Direct content field
            if "content" in result:
                return result["content"]
            
            # Agent output field
            if "agent_output" in result:
                return result["agent_output"]
        
        # Fallback: convert to string
        return str(result)

    def invoke(self, state: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke method for LangGraph compatibility.
        
        This method provides compatibility with LangGraph workflows
        and supervisor patterns.
        
        Args:
            state: State dictionary from workflow
            config: Optional configuration dictionary
            
        Returns:
            Updated state dictionary
        """
        try:
            # Extract user input from state
            user_input = ""
            
            if "messages" in state:
                messages = state["messages"]
                # Find the last user message
                for message in reversed(messages):
                    if hasattr(message, "type") and message.type in ("user", "human"):
                        user_input = message.content
                        break
                    elif isinstance(message, dict):
                        role = message.get("role", "")
                        if role in ("user", "human"):
                            user_input = message.get("content", "")
                            break
            else:
                user_input = state.get("user_input", state.get("query", ""))
            
            if not user_input:
                return {"messages": [{"role": "assistant", "content": "No input provided"}]}
            
            # Process the query
            result = self.query(user_input)
            
            # Return result in LangGraph format
            return {"messages": [{"role": "assistant", "content": result}]}
        
        except Exception as e:
            error_msg = f"Root agent processing error: {e}"
            return {"messages": [{"role": "assistant", "content": error_msg}]}

    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the current workflow.
        
        Returns:
            Dictionary containing workflow information
        """
        info = {
            "agent_name": self.name,
            "agent_type": "RootAgent",
            "memory_enabled": self.enable_memory,
            "workflow_initialized": self.workflow is not None,
        }
        
        if hasattr(self.workflow, "__class__"):
            info["workflow_type"] = self.workflow.__class__.__name__
        
        return info


class SupervisorAgent(RootAgent):
    """Specialized RootAgent for supervisor-based multi-agent systems.
    
    This class provides additional utilities specifically for coordinating
    multiple subagents in a supervisor pattern.
    """

    def __init__(
        self,
        llm: Any,
        subagents: Optional[List[Any]] = None,
        supervisor_prompt: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        enable_memory: bool = True,
        resume_session: Optional[bool] = None,
        **kwargs: Any
    ):
        """Initialize SupervisorAgent with subagent configuration.
        
        Args:
            llm: Language model instance
            subagents: List of subagent instances
            supervisor_prompt: Custom supervisor prompt
            config: Agent configuration dictionary
            name: Agent name for identification
            enable_memory: Whether to enable memory system (default: True)
            resume_session: Whether to resume from previous session
            **kwargs: Additional configuration parameters
        """
        self.subagents = subagents or []
        
        # Use supervisor prompt as the agent prompt
        prompt = supervisor_prompt or self._get_default_supervisor_prompt()
        
        super().__init__(
            llm=llm,
            config=config,
            name=name or "supervisor",
            prompt=prompt,
            enable_memory=enable_memory,
            resume_session=resume_session,
            **kwargs
        )

    def _get_default_supervisor_prompt(self) -> str:
        """Get default supervisor prompt.
        
        Returns:
            Default supervisor prompt string
        """
        return """You are a team supervisor managing multiple specialized agents.

Your role is to:
1. Analyze user queries and determine the most appropriate agent to handle them
2. Route queries to the correct agent based on the query content and agent capabilities
3. Return agent responses without modification or summarization
4. Coordinate multi-step tasks that require multiple agents

Available agents and their capabilities:
{}

When an agent provides a response, return their complete response unchanged.
Do not modify, summarize, or paraphrase agent responses.
""".format(self._format_agent_capabilities())

    def _format_agent_capabilities(self) -> str:
        """Format agent capabilities for the supervisor prompt.
        
        Returns:
            Formatted string describing agent capabilities
        """
        if not self.subagents:
            return "- No subagents configured"
        
        capabilities = []
        for i, agent in enumerate(self.subagents):
            agent_name = getattr(agent, "name", f"Agent_{i}")
            agent_type = agent.__class__.__name__
            capabilities.append(f"- {agent_name} ({agent_type}): Specialized agent")
        
        return "\n".join(capabilities)

    def create_workflow(self) -> Any:
        """Create supervisor workflow with configured subagents.
        
        This default implementation creates a basic supervisor workflow.
        Subclasses can override this for custom workflow creation.
        
        Returns:
            Compiled supervisor workflow
        """
        try:
            from ..agent.app_utils import create_supervisor_workflow
            
            if not self.subagents:
                # Create a simple workflow without subagents
                return self._create_simple_workflow()
            
            # Create supervisor workflow with subagents
            return create_supervisor_workflow(
                self.subagents, 
                self.llm, 
                self._get_default_prompt()
            )
        
        except ImportError:
            # Fallback if supervisor workflow utilities are not available
            return self._create_simple_workflow()

    def _create_simple_workflow(self) -> Any:
        """Create a simple workflow for cases without subagents.
        
        Returns:
            Simple workflow that uses the supervisor LLM directly
        """
        # This is a simplified implementation
        # In practice, you might want to create a basic LangGraph workflow
        class SimpleWorkflow:
            def __init__(self, llm):
                self.llm = llm
            
            def invoke(self, input_data):
                messages = input_data.get("messages", [])
                if messages:
                    # Simple LLM call
                    last_message = messages[-1]
                    if isinstance(last_message, dict):
                        content = last_message.get("content", "")
                    else:
                        content = str(last_message)
                    
                    # This is a simplified response
                    return {"messages": [{"role": "assistant", "content": f"Processed: {content}"}]}
                
                return {"messages": [{"role": "assistant", "content": "No input provided"}]}
        
        return SimpleWorkflow(self.llm)

    def add_subagent(self, agent: Any) -> None:
        """Add a subagent to the supervisor.
        
        Args:
            agent: Subagent instance to add
        """
        self.subagents.append(agent)
        # Recreate workflow with new agent
        self.workflow = self.create_workflow()

    def remove_subagent(self, agent: Any) -> None:
        """Remove a subagent from the supervisor.
        
        Args:
            agent: Subagent instance to remove
        """
        if agent in self.subagents:
            self.subagents.remove(agent)
            # Recreate workflow without the agent
            self.workflow = self.create_workflow()

    def get_subagent_info(self) -> List[Dict[str, Any]]:
        """Get information about all subagents.
        
        Returns:
            List of dictionaries containing subagent information
        """
        info = []
        for i, agent in enumerate(self.subagents):
            agent_info = {
                "index": i,
                "name": getattr(agent, "name", f"Agent_{i}"),
                "type": agent.__class__.__name__,
                "memory_enabled": getattr(agent, "enable_memory", False),
                "initialized": getattr(agent, "is_initialized", False),
            }
            info.append(agent_info)
        
        return info