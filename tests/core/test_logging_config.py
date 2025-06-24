"""Tests for agentdk.core.logging_config module."""

import logging
import pytest
from unittest.mock import patch, MagicMock
from agentdk.core.logging_config import get_logger, set_log_level, ensure_nest_asyncio, _setup_logger


def test_get_logger_returns_logger():
    """Test that get_logger returns a proper logger instance."""
    logger = get_logger()
    
    assert isinstance(logger, logging.Logger)
    assert logger.name == "agentdk"
    assert logger.level == logging.INFO  # Default level


def test_get_logger_singleton_behavior():
    """Test that get_logger returns the same instance on multiple calls."""
    logger1 = get_logger()
    logger2 = get_logger()
    logger3 = get_logger("agentdk")
    
    assert logger1 is logger2
    assert logger1 is logger3


def test_set_log_level_changes_level():
    """Test that set_log_level properly changes the logging level."""
    logger = get_logger()
    
    # Test setting to DEBUG
    set_log_level("DEBUG")
    assert logger.level == logging.DEBUG
    
    # Test setting to WARNING
    set_log_level("WARNING")
    assert logger.level == logging.WARNING
    
    # Test setting to ERROR
    set_log_level("ERROR")
    assert logger.level == logging.ERROR


def test_set_log_level_invalid_level():
    """Test that set_log_level raises ValueError for invalid levels."""
    with pytest.raises(ValueError, match="Invalid log level"):
        set_log_level("INVALID_LEVEL")
    
    with pytest.raises(ValueError, match="Invalid log level"):
        set_log_level("not_a_level")


def test_ensure_nest_asyncio_without_ipython():
    """Test ensure_nest_asyncio handles non-IPython environment gracefully."""
    # Should not raise any exception when not in IPython
    try:
        ensure_nest_asyncio()
    except Exception as e:
        pytest.fail(f"ensure_nest_asyncio raised an exception: {e}") 