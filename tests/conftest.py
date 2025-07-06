"""Shared test configuration and fixtures for AgentDK tests.

This module provides common fixtures and configuration for all tests,
following the organized test structure that mirrors src/agentdk/.
"""

import pytest
import tempfile
import os
import asyncio
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

# Ensure nest_asyncio is available for tests
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# Configure asyncio for pytest
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def mock_llm():
    """Fixture providing a mock LLM instance for testing."""
    llm = Mock()
    llm.invoke.return_value = "Mock LLM response"
    return llm


@pytest.fixture
def sample_mcp_config():
    """Fixture providing a valid MCP configuration for testing."""
    return {
        "mysql": {
            "command": "uv",
            "args": ["--directory", "/path/to/server", "run", "mysql_mcp_server"],
            "env": {
                "MYSQL_HOST": "localhost",
                "MYSQL_PORT": "3306",
                "MYSQL_USER": "root",
                "MYSQL_PASSWORD": "password",
                "MYSQL_DATABASE": "testdb"
            }
        }
    }


@pytest.fixture
def mock_memory_config():
    """Fixture providing mock memory configuration for testing."""
    return {
        "memory_max_context_tokens": 2048,
        "memory_enable_summarization": True,
        "memory_context_strategy": "prioritized"
    }


@pytest.fixture
def mock_memory_manager():
    """Fixture providing a mock memory manager for testing."""
    manager = MagicMock()
    manager.user_id = "test_user"
    manager.session_id = "test_session"
    manager.add_interaction.return_value = None
    manager.get_relevant_context.return_value = {
        "episodic_memories": [],
        "factual_knowledge": [],
        "user_preferences": {}
    }
    manager.get_stats.return_value = {
        "total_interactions": 0,
        "episodic_memories": 0,
        "factual_entries": 0
    }
    return manager


@pytest.fixture
def temporary_prompt_file():
    """Fixture providing a temporary prompt file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("You are a helpful test assistant.")
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def test_agent_config():
    """Fixture providing complete agent configuration for testing."""
    return {
        "llm": Mock(),
        "prompt": "You are a test agent.",
        "name": "test_agent",
        "tools": [],
        "mcp_config_path": None
    } 