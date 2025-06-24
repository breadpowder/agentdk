"""Research Agent example demonstrating minimal boilerplate with optimized SubAgentInterface.

This shows how easy it is to create new agents now that common logic is centralized.
"""

from typing import Any, Dict

from agentdk.agent.agent_interface import SubAgentInterface
from agentdk.core.logging_config import ensure_nest_asyncio
from .prompts import get_research_agent_prompt

# Ensure async compatibility for IPython/Jupyter
ensure_nest_asyncio()


class ResearchAgent(SubAgentInterface):
    """Research Agent for web research and information gathering.
    
    This agent demonstrates the minimal code needed to create a new agent
    with the optimized SubAgentInterface handling all common logic.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Research Agent.
        
        Args:
            **kwargs: Arguments passed to SubAgentInterface
        """
        # Set default name if not provided
        if 'name' not in kwargs:
            kwargs['name'] = 'research_agent'
        super().__init__(**kwargs)

    def _get_default_prompt(self) -> str:
        """Get the default system prompt for research tasks.
        
        Returns:
            Default system prompt for research
        """
        return get_research_agent_prompt()

    async def _create_langgraph_agent(self) -> None:
        """Create the LangGraph reactive agent with research tools."""
        try:
            from langgraph.prebuilt import create_react_agent
            
            # Create react agent with the LLM and wrapped tools
            self.agent = create_react_agent(self.llm, self._tools)
            
            self.logger.info(f"Created Research LangGraph agent with {len(self._tools)} tools")
            
        except ImportError as e:
            self.logger.error(f"Failed to import LangGraph: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to create Research LangGraph agent: {e}")
            raise

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state for LangGraph workflow integration.
        
        Args:
            state: Current state dictionary from the graph
            
        Returns:
            Updated state dictionary with research results
        """
        try:
            # Extract user input from state
            user_input = state.get('user_input', state.get('query', ''))
            
            if not user_input:
                self.logger.warning("No user input found in state")
                state['research_analysis'] = "No research query provided"
                state['agent_output'] = state['research_analysis']
                return state

            # Process the query using inherited method
            research_result = self.query(user_input)
            
            # Update state with results
            state['research_analysis'] = research_result
            state['agent_output'] = research_result
            state['agent_type'] = 'research'
            
            self.logger.info("Research analysis completed successfully")
            return state

        except Exception as e:
            error_msg = f"Research processing error: {e}"
            self.logger.error(error_msg)
            
            state['research_analysis'] = error_msg
            state['agent_output'] = error_msg
            state['error'] = str(e)
            
            return state


# Factory function for backward compatibility
def create_research_agent(llm: Any = None, log_level: str = "INFO") -> ResearchAgent:
    """Create a Research agent instance.
    
    Args:
        llm: Language model instance
        log_level: Logging level
        
    Returns:
        Configured Research agent
    """
    # Set up logging level
    from agentdk.core.logging_config import set_log_level
    set_log_level(log_level)
    
    # Create agent with simplified interface
    return ResearchAgent(llm=llm) 