"""Shared fixtures and configuration for integration tests."""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional


def pytest_configure(config):
    """Add integration test markers and configuration."""
    config.addinivalue_line(
        "markers", 
        "integration: marks tests as integration tests requiring API keys"
    )


@pytest.fixture(scope="session")
def openai_api_key() -> Optional[str]:
    """Fixture to provide OPENAI_API_KEY or skip tests."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set - skipping integration test")
    return api_key


@pytest.fixture(scope="session")
def anthropic_api_key() -> Optional[str]:
    """Fixture to provide ANTHROPIC_API_KEY (optional)."""
    return os.getenv("ANTHROPIC_API_KEY")


@pytest.fixture(scope="session")
def agent_examples_path():
    """Path to main agent example for testing."""
    return "examples/agent_app.py"


@pytest.fixture(scope="session")
def eda_agent_path():
    """Path to EDA agent example for testing."""
    return "examples/subagent/eda_agent.py"


@pytest.fixture(scope="function")
def clean_session_environment():
    """Ensure clean session environment for each test."""
    import subprocess
    
    # Use agentdk command to clear all sessions before test
    print("🧹 Clearing all agent sessions before test...")
    try:
        result = subprocess.run([
            "uv", "run", "python", "-m", "agentdk.cli.main", 
            "sessions", "clear", "--all"
        ], 
        capture_output=True, 
        text=True, 
        cwd="/home/zineng/workspace/agentic/agentdk",
        env=os.environ.copy(),
        timeout=30
        )
        if result.returncode == 0:
            print(f"✅ Sessions cleared: {result.stdout.strip()}")
        else:
            print(f"⚠️  Session clear returned code {result.returncode}: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⚠️  Session clear command timed out")
    except Exception as e:
        print(f"⚠️  Could not clear sessions before test: {e}")
    
    yield
    
    # Note: We don't restore sessions after test to avoid interference
    # Integration tests should be idempotent and not depend on previous state


@pytest.fixture(scope="function")
def temp_working_dir():
    """Provide a temporary working directory for test isolation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        yield temp_dir
        os.chdir(original_cwd)


@pytest.fixture(scope="session")
def integration_test_queries():
    """Standard test queries for agent testing."""
    return {
        "no_context": "which table you last accessed",
        "list_tables": "list table", 
        "customer_count": "how many customers you have",
        "previous_table": "which table i just accessed?",
        "previous_query": "which query i just run?",
        "case_sensitive_fail": "what the average amount from chequing account",
        "case_sensitive_success": "what the max amount from saving account"
    }