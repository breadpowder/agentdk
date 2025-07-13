"""Top-level agent example demonstrating LangGraph supervisor with multiple agents.

This example shows how to use the AgentDK with a supervisor pattern as specified 
in design_doc.md. Enhanced with memory integration for conversation continuity
and user preference support.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Optional, Dict

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from the same directory as this script
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    print(f"✅ Environment variables loaded from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables only.")
    print("   Install with: pip install python-dotenv")

# Import AgentDK components
from subagent.eda_agent import create_eda_agent
from subagent.research_agent import create_research_agent
from agentdk.core.logging_config import ensure_nest_asyncio
from agentdk.agent.base_app import RootAgent, create_memory_session
from agentdk.agent.app_utils import create_supervisor_workflow

# Ensure async compatibility for IPython/Jupyter
ensure_nest_asyncio()

class App(RootAgent):
    """Clean application with dependency injection architecture.
    
    Combines application logic + agent interface with proper separation of concerns.
    """

    def __init__(
        self, 
        llm: Any,
        memory: bool = True,
        user_id: str = "default",
        memory_config: Optional[Dict[str, Any]] = None,
        resume_session: Optional[bool] = None
    ):
        """Initialize App with dependency injection and multiple inheritance.
        
        Args:
            llm: Language model instance
            memory: Whether to enable memory system
            user_id: User identifier for scoped memory
            memory_config: Optional memory configuration
            resume_session: Whether to resume from previous session
        """
        # Create memory session via factory (dependency injection)
        memory_session = create_memory_session(
            name="supervisor_app",
            user_id=user_id,
            enable_memory=memory,
            memory_config=memory_config
        )
        
        # Initialize with dependency injection (multiple inheritance)
        super().__init__(
            memory_session=memory_session,
            name="supervisor_app",
            resume_session=resume_session
        )
        
        self.llm = llm
        self.workflow = self.create_workflow(llm)
    

    def create_workflow(self, llm: Any) -> Any:
        """Implement workflow creation.
        
        Args:
            llm: Language model instance
            
        Returns:
            LangGraph workflow with supervisor pattern
        """
        def web_search(query: str) -> str:
            """Search the web for information."""
            return (
                "Here are the headcounts for each of the FAANG companies in 2024:\n"
                "1. **Facebook (Meta)**: 67,317 employees.\n"
                "2. **Apple**: 164,000 employees.\n"
                "3. **Amazon**: 1,551,000 employees.\n"
                "4. **Netflix**: 14,000 employees.\n"
                "5. **Google (Alphabet)**: 181,269 employees."
            )
        
        # Create subagents with dependency injection
        eda_agent = create_eda_agent(
            llm=llm,
            mcp_config_path="subagent/mcp_config.json",
            memory_session=None,  # App handles memory, subagents don't need it
            enable_memory = False
        )
        research_agent = create_research_agent(
            llm=llm,
            tools=[web_search],
            memory_session=None,
            enable_memory= False
        )
        
        supervisor_prompt = self._create_supervisor_prompt()
        return create_supervisor_workflow([research_agent, eda_agent], llm, supervisor_prompt)
    
    def clean_app(self) -> None:
        """Cleanup application resources."""
        # Cleanup workflow and resources
        if hasattr(self, 'workflow'):
            # Add any specific cleanup logic here
            pass
    
    def _process_query(self, user_prompt: str, enhanced_input: Dict) -> str:
        """Process using workflow."""
        messages = self._create_workflow_messages(user_prompt, enhanced_input)
        result = self.workflow.invoke({"messages": messages})
        return self._extract_response(result)
    
    def _create_workflow_messages(self, user_prompt: str, enhanced_input: Dict) -> list:
        """Create workflow messages from query and enhanced input."""
        from agentdk.agent.app_utils import create_workflow_messages
        return create_workflow_messages(user_prompt, enhanced_input)
    
    def _extract_response(self, result: Any) -> str:
        """Extract response from workflow result."""
        from agentdk.agent.app_utils import extract_response
        return extract_response(result)
    
    def _create_supervisor_prompt(self) -> str:
        """Create supervisor prompt with memory awareness."""
        base_prompt = """You are a team supervisor managing a research expert and an EDA agent.
        
        CRITICAL ROUTING RULES:
        
        Use 'eda_agent' for ANY question about:
        - Database tables, table access, table information
        - SQL queries, data exploration, data analysis
        - Exploratory data analysis (EDA)
        - Financial data analysis
        
        Use 'research_expert' for:
        - Current events, news, web search
        - General information not in the database
        - Company information not stored in database
        
        CRITICAL RESPONSE RULES:
        1. When an agent provides a response, ALWAYS return the COMPLETE response exactly as provided.
        2. If the EDA agent returns SQL queries with results, preserve the ENTIRE response including:
           - The SQL code blocks
           - The result sections
           - All formatting and structure
        3. DO NOT extract only the final answer - return the full response with SQL + results.
        4. DO NOT summarize, paraphrase, or modify the agent's response in any way.
        5. DO NOT modify, edit, or change the agent's response format, content, or structure.
        6. Your job is to route to the correct agent and return their complete response unchanged.
        
        When in doubt about data-related questions, ALWAYS choose eda_agent."""
        
        # Add memory awareness if available
        return self.get_memory_aware_prompt(base_prompt)
    
    def _get_default_prompt(self) -> str:
        """Get the default system prompt for this supervisor app.
        
        Returns:
            Default supervisor system prompt
        """
        return """You are a team supervisor managing a research expert and an EDA agent.
        
        CRITICAL ROUTING RULES:
        
        Use 'eda_agent' for ANY question about:
        - Database tables, table access, table information
        - SQL queries, data exploration, data analysis
        - Exploratory data analysis (EDA)
        - Financial data analysis
        
        Use 'research_expert' for:
        - Current events, news, web search
        - General information not in the database
        - Company information not stored in database
        
        When in doubt about data-related questions, ALWAYS choose eda_agent."""

