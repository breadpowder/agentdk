"""Centralized logging configuration for AgentDK.

This module provides project-level logger initialization with IPython/Jupyter compatibility.
Default level is set to INFO as specified in the requirements.
"""

import logging
import sys
from typing import Optional

# Global logger instance
_agentdk_logger: Optional[logging.Logger] = None


def get_logger(name: str = "agentdk") -> logging.Logger:
    """Get or create a logger instance for AgentDK.
    
    Args:
        name: Logger name (defaults to 'agentdk')
        
    Returns:
        Configured logger instance
    """
    global _agentdk_logger
    
    if _agentdk_logger is None:
        _agentdk_logger = _setup_logger(name)
    
    return _agentdk_logger


def _setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up logger with IPython/Jupyter compatibility.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    # Prevent propagation to root logger to avoid duplicates in Jupyter
    logger.propagate = False
    
    return logger


def set_log_level(level: str) -> None:
    """Set the logging level for AgentDK logger.
    
    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    global _agentdk_logger
    
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    if _agentdk_logger is None:
        _agentdk_logger = _setup_logger("agentdk", numeric_level)
    else:
        _agentdk_logger.setLevel(numeric_level)
        for handler in _agentdk_logger.handlers:
            handler.setLevel(numeric_level)


def ensure_nest_asyncio() -> None:
    """Ensure nest_asyncio is applied for IPython/Jupyter compatibility.
    
    This function checks if we're in an IPython environment and applies
    nest_asyncio if needed for async pattern support.
    """
    try:
        # Check if we're in IPython/Jupyter
        get_ipython()  # type: ignore[name-defined]
        
        # Apply nest_asyncio for async compatibility
        import nest_asyncio
        nest_asyncio.apply()
        
        logger = get_logger()
        logger.debug("nest_asyncio applied for IPython/Jupyter compatibility")
        
    except NameError:
        # Not in IPython, no need for nest_asyncio
        pass
    except ImportError:
        logger = get_logger()
        logger.warning("nest_asyncio not available, async patterns may not work in Jupyter")


# Initialize logging on module import
_agentdk_logger = _setup_logger("agentdk") 