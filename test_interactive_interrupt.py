#!/usr/bin/env python3
"""Test script to simulate interactive interrupt behavior."""

import subprocess
import time
import signal
import sys

def test_interrupt():
    """Test the interrupt behavior with real agent."""
    
    # Start the agent process
    print("Starting agent process...")
    
    env = {"OPENAI_API_KEY": "your_key_here"}  # Will use actual env key
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "agentdk.cli.main", "run", "examples/agent_app.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    try:
        # Give it time to start up
        time.sleep(3)
        
        # Send a query
        print("Sending query...")
        proc.stdin.write("how many customers?\n")
        proc.stdin.flush()
        
        # Wait for processing
        time.sleep(5)
        
        # Send interrupt signal
        print("Sending interrupt signal...")
        proc.send_signal(signal.SIGINT)
        
        # Wait for termination
        try:
            stdout, stderr = proc.communicate(timeout=10)
            print("Process terminated successfully")
            print("Exit code:", proc.returncode)
            
            if "Gracefully shutting down" in stderr:
                print("✅ Graceful shutdown detected")
            else:
                print("❌ No graceful shutdown message")
                
        except subprocess.TimeoutExpired:
            print("❌ Process did not terminate - killing it")
            proc.kill()
            stdout, stderr = proc.communicate()
            
        print("\n--- STDOUT ---")
        print(stdout)
        print("\n--- STDERR ---") 
        print(stderr)
        
    except Exception as e:
        print(f"Error: {e}")
        proc.kill()

if __name__ == "__main__":
    test_interrupt()