"""Tests for agentdk package.

Test Structure:
---------------
- test_exceptions.py: Tests for custom exception classes (5 tests)  
- test_init.py: Tests for main package initialization (5 tests)
- core/test_logging_config.py: Tests for logging configuration (5 tests)
- core/test_mcp_load.py: Tests for MCP configuration loading (5 tests)
- agent/test_factory.py: Tests for agent factory functions (5 tests)

Total: 25 basic unit tests covering the core functionality of AgentDK.

Running Tests:
--------------
Run all tests: python -m pytest tests/ -v
Run specific module: python -m pytest tests/test_exceptions.py -v
Run with coverage: python -m pytest tests/ --cov=src/agentdk
""" 