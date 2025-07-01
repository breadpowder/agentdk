import os

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

