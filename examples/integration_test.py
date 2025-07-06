#!/usr/bin/env python3
"""Integration test following agentdk_testing_notebook.ipynb flow.

This script follows the exact test flow from the notebook:
1. Setup LLM 
2. Create App agent with memory
3. Run test queries from notebook
4. Verify results

Usage:
    python integration_test.py

Prerequisites:
    1. Run setup.sh to configure MySQL environment
    2. Set API keys in .env file (OPENAI_API_KEY or ANTHROPIC_API_KEY)
"""

import os
import sys
from pathlib import Path

# Load environment variables - same as notebook
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    print(f"✅ Environment variables loaded from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Add src to path - same as notebook  
sys.path.insert(0, str(Path.cwd().parent / 'src'))

# Import components - same as notebook
from subagent.eda_agent import create_eda_agent
from agent_app import App
from agentdk.core.logging_config import ensure_nest_asyncio

def get_llm():
    """Get LLM - exact same function as notebook."""
    # Try OpenAI
    if os.getenv('OPENAI_API_KEY'):
        try:
            from langchain_openai import ChatOpenAI
            model = "gpt-4o-mini"
            llm = ChatOpenAI(model=model, temperature=0)
            print(f"✅ Using OpenAI {model}")
            return llm
        except ImportError:
            print("❌ langchain_openai not available")
        except Exception as e:
            print(f"❌ OpenAI setup failed: {e}")
    
    # Try Anthropic
    elif os.getenv('ANTHROPIC_API_KEY'):
        try:
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)
            print("✅ Using Anthropic Claude-3-Haiku")
            return llm
        except ImportError:
            print("❌ langchain_anthropic not available")
        except Exception as e:
            print(f"❌ Anthropic setup failed: {e}")

    else:
        raise ValueError("No LLM API key found")

def test_builder_pattern_directly():
    """Test the builder pattern directly without App wrapper."""
    print("\n3. Testing builder pattern directly...")
    
    # Get LLM
    llm = get_llm()
    
    try:
        # Test EDA agent creation using builder pattern
        print("   Creating EDA agent using builder pattern...")
        eda_agent = create_eda_agent(
            llm=llm,
            mcp_config_path="subagent/mcp_config.json"
        )
        print("   ✅ EDA agent created successfully")
        
        # Test a simple query
        print("   Testing EDA agent query...")
        result = eda_agent.query("which table i have access to?")
        print(f"   ✅ EDA agent query completed ({len(result)} chars)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Builder pattern test failed: {e}")
        return False

def main():
    """Main test following notebook flow."""
    print("🚀 AgentDK Integration Test")
    print("Following agentdk_testing_notebook.ipynb flow with builder pattern")
    print("=" * 60)
    
    # Get LLM instance - same as notebook
    llm = get_llm()
    
    # Create agent with memory - same as notebook
    print("\n1. Creating App agent with memory...")
    agent = App(model=llm, memory=True)
    print("✅ Agent created successfully")
    
    # Test queries from notebook in exact order
    test_queries = [
        "which table i have access to?",
        "what is the total transaction amount from customer 'John Smith'",
        "give me 2 records from table 'trans'", 
        "which table i just accessed"
    ]
    
    print(f"\n2. Running {len(test_queries)} test queries...")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Query {i}: {query} ---")
        try:
            result = agent(query)
            print(f"✅ Query {i} completed")
            print(f"Result length: {len(result)} characters")
            # Show first 200 chars of result
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"Preview: {preview}")
        except Exception as e:
            print(f"❌ Query {i} failed: {e}")
            return 1
    
    print(f"\n🎉 All {len(test_queries)} queries completed successfully!")
    
    # Test builder pattern directly
    if not test_builder_pattern_directly():
        return 1
    
    print("\n🎉 All tests passed! Builder pattern working correctly!")
    print("Integration test passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())