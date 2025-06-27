import os
import sys
import asyncio
import json
from typing import Any, Dict, List
from pathlib import Path
# Add the src directory to Python path for imports
sys.path.insert(0, str(Path.cwd().parent / 'src'))
from subagent.eda_agent import EDAAgent
from agent_app import App
from agentdk.core.logging_config import ensure_nest_asyncio


def get_llm():    
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
    # Fallback to mock
    return llm

# Get LLM instance
llm = get_llm()

agent = App(model=llm, memory=False)
print(agent(f"what is the total transaction amount from customer 'John Smith'"))

import time
print("sleep waiting")
time.sleep(20)

print("trying again")
print(agent(f"what is the total transaction amount from customer 'John Smith'"))





