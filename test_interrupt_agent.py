#!/usr/bin/env python3
"""Simple test agent for testing interrupt handling."""

import time

class TestInterruptAgent:
    """Test agent that simulates long-running operations."""
    
    def __init__(self, **kwargs):
        pass
    
    def query(self, user_prompt: str, **kwargs) -> str:
        """Process query with simulated long-running operation."""
        print(f"Processing query: {user_prompt}")
        
        # Simulate a long-running operation
        if "slow" in user_prompt.lower():
            print("Starting slow operation... (try Ctrl+C)")
            for i in range(10):
                print(f"Working... step {i+1}/10")
                time.sleep(1)
            return "Slow operation completed!"
        
        return f"Quick response to: {user_prompt}"

# Create the agent instance for CLI loading
def create_agent(**kwargs):
    """Factory function to create the agent."""
    return TestInterruptAgent(**kwargs)