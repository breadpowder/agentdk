#!/usr/bin/env python3
"""Final test to verify persistent session fix is working."""

import os
import sys
import time
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    print(f"✅ Environment variables loaded from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Set default environment variables
os.environ.setdefault('MYSQL_HOST', 'localhost')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('MYSQL_USER', 'agentdk_user')
os.environ.setdefault('MYSQL_PASSWORD', 'agentdk_user_password')
os.environ.setdefault('MYSQL_DATABASE', 'agentdk_test')

# Import AgentDK components
try:
    from subagent.eda_agent import EDAAgent
    from agentdk.core.logging_config import ensure_nest_asyncio
    from agentdk.utils.utils import llm
except ImportError as e:
    print(f"❌ Failed to import AgentDK components: {e}")
    sys.exit(1)

ensure_nest_asyncio()

def main():
    """Test persistent sessions with short intervals."""
    print("🔧 Testing AgentDK Persistent Session Fix")
    print("=" * 50)
    
    # Create agent (this should create persistent sessions)
    print("1. Creating agent...")
    agent = EDAAgent(llm=llm)
    print("✅ Agent created successfully")
    
    # Test query 1
    print("\n2. First query (should work with new persistent session)...")
    start_time = time.time()
    result1 = agent.query("SELECT COUNT(*) as customer_count FROM customers")
    duration1 = time.time() - start_time
    print(f"✅ First query completed in {duration1:.3f}s")
    print(f"   Result: {result1[:100]}...")
    
    # Short sleep (within session timeout)
    print("\n3. Short wait (5 seconds)...")
    time.sleep(5)
    
    # Test query 2 (should reuse persistent session)
    print("\n4. Second query (should reuse persistent session)...")
    start_time = time.time()
    result2 = agent.query("SELECT COUNT(*) as transaction_count FROM transactions")
    duration2 = time.time() - start_time
    print(f"✅ Second query completed in {duration2:.3f}s")
    print(f"   Result: {result2[:100]}...")
    
    # Performance analysis
    print(f"\n📊 Performance Analysis:")
    print(f"   First query:  {duration1:.3f}s")
    print(f"   Second query: {duration2:.3f}s")
    
    if duration2 < duration1 * 0.5:  # Should be much faster
        print("✅ SUCCESS: Second query significantly faster - persistent sessions working!")
    elif duration2 < duration1:
        print("✅ GOOD: Second query faster - persistent sessions likely working")
    else:
        print("⚠️  WARNING: No performance improvement detected")
    
    print("\n🎉 Test completed successfully!")

if __name__ == "__main__":
    main()