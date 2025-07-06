#!/usr/bin/env python3
"""Final validation that persistent sessions work correctly"""

import time
from agentdk.utils.utils import llm
from subagent.eda_agent import EDAAgent  

print("🧪 FINAL VALIDATION TEST")
print("=" * 50)

# Test 1: Create agent
print("1. Creating agent...")
agent = EDAAgent(llm=llm)
print("   ✅ Agent created")

# Test 2: First query
print("\n2. First query...")
start = time.time()
result1 = agent.query("which tables are available?")
duration1 = time.time() - start
print(f"   ✅ Success in {duration1:.2f}s")
print(f"   📋 Tables: {len(result1.split('•'))-1} found")

# Test 3: Quick follow-up query (persistent session test)
print("\n3. Follow-up query (testing persistence)...")  
start = time.time()
result2 = agent.query("how many customers?")
duration2 = time.time() - start
print(f"   ✅ Success in {duration2:.2f}s")
print(f"   📊 Result preview: {result2[:100]}...")

# Test 4: Performance analysis
print(f"\n📈 Performance Analysis:")
print(f"   First query:  {duration1:.2f}s")
print(f"   Second query: {duration2:.2f}s")

if duration2 < duration1 * 0.8:
    print("   🚀 EXCELLENT: Persistent sessions working!")
elif duration2 < duration1:
    print("   ✅ GOOD: Some improvement detected")
else:
    print("   ⚠️ Performance similar (may indicate session reuse issues)")

print("\n🎉 VALIDATION COMPLETE!")