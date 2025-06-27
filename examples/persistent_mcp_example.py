#!/usr/bin/env python3
"""Example demonstrating persistent MCP session usage."""

import asyncio
from pathlib import Path
from subagent.eda_agent import EDAAgent

async def example_persistent_sessions():
    """Demonstrate how to use persistent MCP sessions properly."""
    
    print("🔧 PERSISTENT MCP SESSIONS EXAMPLE")
    print("="*50)
    
    # Method 1: Using async context manager (RECOMMENDED)
    print("\n📝 Method 1: Async Context Manager (Recommended)")
    print("-" * 50)
    
    async with EDAAgent() as agent:
        print("✅ Agent created with persistent sessions")
        
        # These queries will reuse the same MCP server connections
        queries = [
            "What tables are available in the database?",
            "Show me the first 5 users",
            "How many users are in the database?",
            "What is the average age of users?"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n🔍 Query {i}: {query}")
            result = await agent.query_async(query)
            print(f"📊 Result: {result[:150]}..." if len(result) > 150 else f"📊 Result: {result}")
    
    print("\n✅ Sessions automatically cleaned up when exiting context")
    
    # Method 2: Manual cleanup (NOT RECOMMENDED but possible)
    print("\n📝 Method 2: Manual Cleanup (Not Recommended)")
    print("-" * 50)
    
    agent = EDAAgent()
    try:
        result = await agent.query_async("SELECT COUNT(*) FROM users")
        print(f"📊 Manual result: {result}")
    finally:
        # IMPORTANT: Always cleanup manually if not using context manager
        await agent.cleanup()
        print("✅ Manual cleanup completed")

async def example_performance_benefits():
    """Demonstrate the performance benefits of persistent sessions."""
    
    print("\n⚡ PERFORMANCE BENEFITS DEMONSTRATION")
    print("="*50)
    
    import time
    
    async with EDAAgent() as agent:
        # Multiple queries that would normally recreate connections
        start_time = time.time()
        
        tasks = []
        for i in range(5):
            # These all run concurrently using the same persistent sessions
            task = agent.query_async(f"SELECT {i} as query_number, COUNT(*) FROM users")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"🚀 Completed 5 concurrent queries in {end_time - start_time:.2f} seconds")
        print("💡 With ephemeral sessions, this would have taken much longer!")
        
        for i, result in enumerate(results):
            print(f"   Query {i+1}: {result[:100]}...")

async def example_state_persistence():
    """Demonstrate how state is preserved across queries."""
    
    print("\n💾 STATE PERSISTENCE DEMONSTRATION")  
    print("="*50)
    
    async with EDAAgent() as agent:
        # These queries demonstrate that the MCP server maintains state
        queries = [
            "Show me the structure of the users table",
            "Create a temporary view of active users if possible", 
            "Query the temporary view we just created",
        ]
        
        for query in queries:
            print(f"\n🔄 Executing: {query}")
            result = await agent.query_async(query)
            print(f"📋 Result: {result[:200]}..." if len(result) > 200 else f"📋 Result: {result}")
            
        print("\n💡 Notice how the server remembers the temporary view!")

def main():
    """Run all examples."""
    
    print("🚀 PERSISTENT MCP EXAMPLES")
    print("="*60)
    print("These examples show how the new persistent MCP sessions work.")
    print("The key benefit: MCP servers stay alive between queries!\n")
    
    # Run examples
    asyncio.run(example_persistent_sessions())
    asyncio.run(example_performance_benefits()) 
    asyncio.run(example_state_persistence())
    
    print("\n🎉 ALL EXAMPLES COMPLETED!")
    print("\n📚 Key Takeaways:")
    print("1. Use 'async with EDAAgent() as agent:' for automatic cleanup")
    print("2. Multiple queries reuse the same MCP server connections")
    print("3. State is preserved across queries within the same session")
    print("4. Performance is significantly improved for multiple queries")
    print("5. Always cleanup sessions to avoid resource leaks")

if __name__ == "__main__":
    main()