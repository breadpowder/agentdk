#!/usr/bin/env python3
"""Test script to simulate rapid Ctrl+C presses."""

import subprocess
import signal
import time
import sys
import os

def test_rapid_interrupt():
    """Test rapid interrupt signals."""
    
    print("Testing rapid Ctrl+C behavior...")
    
    # Set environment
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
    
    # Start the agent process
    proc = subprocess.Popen(
        [sys.executable, "-m", "agentdk.cli.main", "run", "examples/agent_app.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        preexec_fn=os.setsid  # Create new process group
    )
    
    try:
        # Give it time to start up
        time.sleep(2)
        
        # Send a query
        print("Sending query...")
        proc.stdin.write("how many customers?\n")
        proc.stdin.flush()
        
        # Wait a bit for query to start
        time.sleep(3)
        
        # Send multiple rapid signals (simulating frantic Ctrl+C)
        print("Sending rapid interrupt signals...")
        for i in range(5):
            print(f"Sending signal {i+1}")
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
            time.sleep(0.1)  # Very rapid
        
        # Wait for termination
        try:
            stdout, stderr = proc.communicate(timeout=10)
            print(f"✅ Process terminated successfully with exit code: {proc.returncode}")
            
            # Count how many signal messages appeared
            signal_count = stderr.count("Received signal 2")
            print(f"Signal handler called {signal_count} times")
            
            if "Gracefully shutting down" in stderr:
                print("✅ Graceful shutdown detected")
            else:
                print("❌ No graceful shutdown message")
                
            if signal_count > 1:
                debug_count = stderr.count("cleanup already in progress")
                print(f"✅ Re-entrancy protection worked: {debug_count} duplicate signals ignored")
                
        except subprocess.TimeoutExpired:
            print("❌ Process did not terminate - test failed")
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            stdout, stderr = proc.communicate()
            return False
            
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except:
            pass
        return False

if __name__ == "__main__":
    success = test_rapid_interrupt()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)