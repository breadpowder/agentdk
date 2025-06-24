"""AgentDK package-specific exceptions."""

from typing import Optional


class AgentDKError(Exception):
    """Base exception for all AgentDK errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        """Initialize AgentDK error.
        
        Args:
            message: Error message
            details: Optional error details dictionary
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MCPConfigError(AgentDKError):
    """Raised when MCP configuration is invalid or missing."""

    def __init__(self, message: str, config_path: Optional[str] = None) -> None:
        """Initialize MCP configuration error.
        
        Args:
            message: Error message
            config_path: Path to the problematic configuration file
        """
        super().__init__(message, {"config_path": config_path})
        self.config_path = config_path


class AgentInitializationError(AgentDKError):
    """Raised when agent initialization fails."""

    def __init__(self, message: str, agent_type: Optional[str] = None) -> None:
        """Initialize agent initialization error.
        
        Args:
            message: Error message
            agent_type: Type of agent that failed to initialize
        """
        super().__init__(message, {"agent_type": agent_type})
        self.agent_type = agent_type 