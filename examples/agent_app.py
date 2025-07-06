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
from agentdk.agent.base_app import BaseMemoryApp
from agentdk.agent.app_utils import create_supervisor_workflow

# Ensure async compatibility for IPython/Jupyter
ensure_nest_asyncio()

class App(BaseMemoryApp):
    """Enhanced App with memory integration.
    
    Provides conversation continuity, user preference support,
    and memory investigation tooling.
    """

    def __init__(
        self, 
        model: Any, 
        memory: bool = True,
        user_id: str = "default",
        memory_config: Optional[Dict[str, Any]] = None,
        resume_session: Optional[bool] = None
    ):
        """Initialize Agent with optional memory integration.
        
        Args:
            model: Language model instance
            memory: Whether to enable memory system
            user_id: User identifier for scoped memory
            memory_config: Optional memory configuration
            resume_session: Whether to resume from previous session (None = no session management)
        """
        # Initialize with base class (which handles model, memory, and workflow creation)
        super().__init__(model=model, memory=memory, user_id=user_id, memory_config=memory_config, resume_session=resume_session)
    

    def create_workflow(self, model: Any) -> Any:
        """Create a supervisor workflow with research and EDA agents.
        
        Args:
            model: Language model instance
            
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
        
        # Create EDA agent with MCP integration using builder pattern
        eda_agent = create_eda_agent(
            llm=model,
            mcp_config_path="subagent/mcp_config.json",
            name="eda_agent"
        )
        
        # Create research agent with web search tool using builder pattern
        research_agent = create_research_agent(
            llm=model,
            tools=[web_search],
            name="research_expert"
        )
        
        # Enhanced supervisor prompt with memory awareness
        supervisor_prompt = self._create_supervisor_prompt()
        
        # Create supervisor workflow using common utility
        return create_supervisor_workflow(
            [research_agent, eda_agent],
            model,
            supervisor_prompt
        )
    
    def _create_supervisor_prompt(self) -> str:
        """Create supervisor prompt with memory awareness.
        
        Returns:
            Enhanced supervisor prompt
        """
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
        
        # Add memory awareness
        return self.get_memory_aware_prompt(base_prompt)

