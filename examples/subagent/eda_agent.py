"""Simplified EDA Agent using AgentDK with enhanced SubAgentInterface.

This simplified version delegates MCP configuration and logging to the AgentDK core,
following the design_doc.md requirement to "offload logic from eda_agent to agent_interface".
"""

from typing import Any, Dict, Optional

from agentdk.agent.agent_interface import SubAgentInterface
from agentdk.core.logging_config import ensure_nest_asyncio
from agentdk.exceptions import AgentInitializationError
from pathlib import Path
from .prompts import get_eda_agent_prompt

# Ensure async compatibility for IPython/Jupyter
ensure_nest_asyncio()


class EDAAgent(SubAgentInterface):
    """Simplified EDA Agent for Exploratory Data Analysis with MCP integration.
    
    This agent provides data analysis capabilities using SQL tools from MCP servers.
    Configuration and initialization are handled by the enhanced SubAgentInterface.
    """
    
    def __init__(self, **kwargs):
        """Initialize the EDA Agent.
        
        Args:
            **kwargs: Arguments passed to SubAgentInterface
        """
        if 'mcp_config_path' not in kwargs:
            kwargs['mcp_config_path'] = str(Path(__file__).parent / 'mcp_config.json')
        # Set default name if not provided
        if 'name' not in kwargs:
            kwargs['name'] = 'eda_agent'
        super().__init__(**kwargs)

    def _get_default_prompt(self) -> str:
        """Get the default system prompt for EDA tasks.
        
        Returns:
            Default system prompt for data analysis
        """
        return get_eda_agent_prompt()

    async def _create_langgraph_agent(self) -> None:
        """Create the LangGraph reactive agent with SQL tools."""
        try:
            from langgraph.prebuilt import create_react_agent
            
            # Create react agent with the LLM and wrapped tools
            self.agent = create_react_agent(self.llm, self._tools, prompt=self._get_default_prompt())
            
            self.logger.info(f"Created LangGraph agent with {len(self._tools)} tools")
            
        except ImportError as e:
            self.logger.error(f"Failed to import LangGraph: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to create LangGraph agent: {e}")
            raise

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state for LangGraph workflow integration.
        
        Args:
            state: Current state dictionary from the graph
            
        Returns:
            Updated state dictionary with EDA results
        """
        try:
            # Extract user input from state
            user_input = state.get('user_input', state.get('query', ''))
            
            if not user_input:
                self.logger.warning("No user input found in state")
                state['eda_analysis'] = "No user input provided for analysis"
                state['agent_output'] = state['eda_analysis']
                return state

            # Process the query using inherited method
            analysis_result = self.query(user_input)
            
            # Update state with results
            state['eda_analysis'] = analysis_result
            state['agent_output'] = analysis_result
            state['agent_type'] = 'eda'
            
            self.logger.info("EDA analysis completed successfully")
            return state

        except Exception as e:
            error_msg = f"EDA processing error: {e}"
            self.logger.error(error_msg)
            
            state['eda_analysis'] = error_msg
            state['agent_output'] = error_msg
            state['error'] = str(e)
            
            return state
    
    def __del__(self):
        """Cleanup when agent is garbage collected."""
        # Note: __del__ is not async, so we can't directly call cleanup()
        # Users should explicitly call cleanup() or use async context manager
        try:
            # During Python shutdown, even basic operations can fail
            # Check if we have the attribute and it's truthy
            if getattr(self, '_persistent_mcp_manager', None):
                import warnings
                warnings.warn(
                    "EDAAgent is being destroyed without proper cleanup. "
                    "Consider using 'async with EDAAgent() as agent:' or "
                    "explicitly calling 'await agent.cleanup()'"
                )
        except (ImportError, RuntimeError, AttributeError, TypeError):
            # Ignore ALL errors during Python shutdown - modules and objects may be unloaded
            # This includes ImportError, RuntimeError, AttributeError, and TypeError
            pass

