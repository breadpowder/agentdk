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
    
# Set default environment variables if not already set
os.environ.setdefault('MYSQL_HOST', 'localhost')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('MYSQL_USER', 'agentdk_user')
os.environ.setdefault('MYSQL_PASSWORD', 'agentdk_user_password')
os.environ.setdefault('MYSQL_DATABASE', 'agentdk_test')
os.environ.setdefault('LOG_LEVEL', 'INFO')
os.environ.setdefault('ENVIRONMENT', 'development')

# Set memory system defaults
os.environ.setdefault('MEMORY_MAX_CONTEXT_TOKENS', '2048')
os.environ.setdefault('MEMORY_ENABLE_SUMMARIZATION', 'true')
os.environ.setdefault('MEMORY_CONTEXT_STRATEGY', 'prioritized')

# Import AgentDK components
from subagent.eda_agent import EDAAgent
from subagent.research_agent import ResearchAgent
from agentdk.core.logging_config import ensure_nest_asyncio
from agentdk.memory import MemoryAwareAgent

# Ensure async compatibility for IPython/Jupyter
ensure_nest_asyncio()

class App(MemoryAwareAgent):
    """Enhanced App with memory integration.
    
    Provides conversation continuity, user preference support,
    and memory investigation tooling.
    """

    def __init__(
        self, 
        model: Any, 
        memory: bool = True,
        user_id: str = "default",
        memory_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Agent with optional memory integration.
        
        Args:
            model: Language model instance
            memory: Whether to enable memory system
            user_id: User identifier for scoped memory
            memory_config: Optional memory configuration
        """
        self.model = model
        
        # Initialize memory system
        super().__init__(memory=memory, user_id=user_id, memory_config=memory_config)
        
        # Create workflow
        self.app = self.create_workflow(model)
    
    def __call__(self, query: str) -> str:
        """Call the agent with memory-enhanced processing.
        
        Args:
            query: User's input query
            
        Returns:
            Agent's response
        """
        # Use memory-aware processing
        enhanced_input = self.process_with_memory(query)
        
        # Format memory context for supervisor forwarding
        memory_context = enhanced_input.get('memory_context')
        if memory_context:
            # Format memory context in a more readable way for LLM
            formatted_context = self._format_memory_context(memory_context)
            formatted_query = f"User query: {query}\nMemory context: {formatted_context}"
            enhanced_input['messages'] = [{"role": "user", "content": formatted_query}]
        else:
            # No memory context available
            enhanced_input['messages'] = [{"role": "user", "content": query}]
        
        # Process with workflow
        result = self.app.invoke(enhanced_input)
        
        # Extract response
        response = self._extract_response(result)
        
        # Finalize with memory
        return self.finalize_with_memory(query, response)
    


    def _extract_response(self, result: Any) -> str:
        """Extract response content from LangGraph result.
        
        Args:
            result: LangGraph workflow result
            
        Returns:
            Extracted response string
        """
        # Extract the content from the LangGraph response to match EDAAgent format
        if isinstance(result, dict) and 'messages' in result:
            messages = result['messages']
            if messages:
                last_message = messages[-1]
                # Extract content from AIMessage or dict format
                if hasattr(last_message, 'content'):
                    return last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    return last_message['content']
        
        # Fallback: return string representation
        return str(result)

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
        
        try:
            from langgraph_supervisor import create_supervisor
            
            # Create EDA agent with MCP integration
            eda_agent = EDAAgent(
                llm=model,
                mcp_config_path="subagent/mcp_config.json",
                name="eda_agent"
            )
            
            # Create research agent with web search tool
            research_agent = ResearchAgent(
                llm=model,
                tools=[web_search],
                name="research_expert",
            )
            
            # Enhanced supervisor prompt with memory awareness
            supervisor_prompt = self._create_supervisor_prompt()
            
            # Create supervisor workflow
            workflow = create_supervisor(
                [research_agent, eda_agent],
                model=model,
                prompt=supervisor_prompt
            )
            app = workflow.compile()
            
            return app
            
        except ImportError as e:
            print(f"Missing required dependency: {e}")
            print("Please install: pip install langgraph langgraph-supervisor")
            raise
        except Exception as e:
            print(f"Failed to create workflow: {e}")
            raise
    
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

