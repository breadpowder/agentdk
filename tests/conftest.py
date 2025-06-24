"""Shared test configuration and fixtures for AgentDK tests."""

import pytest
from unittest.mock import Mock


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