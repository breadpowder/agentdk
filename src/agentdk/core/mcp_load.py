"""MCP configuration loading utilities for AgentDK.

This module provides shared utilities for loading and validating MCP server configurations.
Implements the agent-level config loading strategy with fallback paths.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import inspect

from ..exceptions import MCPConfigError
from .logging_config import get_logger


def get_mcp_config(agent_instance: Any) -> Dict[str, Any]:
    """Load MCP configuration for an agent with fallback strategy.
    
    Args:
        agent_instance: The agent instance requesting configuration
        
    Returns:
        Dictionary containing MCP server configuration
        
    Raises:
        MCPConfigError: If no valid configuration is found or validation fails
    """
    logger = get_logger()
    
    # Get configuration search paths in priority order
    config_paths = _get_config_search_paths(agent_instance)
    
    for path in config_paths:
        if path and path.exists():
            try:
                config = _load_config_file(path)
                _validate_mcp_config(config)
                # Resolve relative paths in the config relative to config file location
                config = _resolve_relative_paths(config, path.parent)
                logger.info(f"Loaded MCP configuration from: {path}")
                return config
            except (json.JSONDecodeError, MCPConfigError) as e:
                logger.warning(f"Invalid config at {path}: {e}")
                continue
    
    # No valid configuration found
    searched_paths = [str(p) for p in config_paths if p]
    raise MCPConfigError(
        f"No valid MCP configuration found. Searched paths: {searched_paths}",
        config_path=str(config_paths[0]) if config_paths else None
    )


def _get_config_search_paths(agent_instance: Any) -> List[Optional[Path]]:
    """Get list of configuration file paths to search in priority order.
    
    Args:
        agent_instance: The agent instance requesting configuration
        
    Returns:
        List of Path objects to search for configuration
    """
    paths = []
    
    # 1. Explicit config path (if provided via constructor)
    if hasattr(agent_instance, '_mcp_config_path') and agent_instance._mcp_config_path:
        paths.append(Path(agent_instance._mcp_config_path))
    
    # 2. Agent location + mcp_config.json (primary default)
    try:
        agent_file = inspect.getfile(agent_instance.__class__)
        agent_dir = Path(agent_file).parent
        paths.append(agent_dir / "mcp_config.json")
    except (OSError, TypeError):
        # Fallback if agent file location can't be determined
        pass
    
    # 3. Current working directory
    paths.append(Path.cwd() / "mcp_config.json")
    
    # 4. Parent directory fallback
    paths.append(Path.cwd().parent / "mcp_config.json")
    
    # 5. Examples directory (for development)
    if Path("examples").exists():
        paths.append(Path("examples") / "mcp_config.json")
        paths.append(Path("examples") / "subagent" / "mcp_config.json")
    
    return paths


def _load_config_file(config_path: Path) -> Dict[str, Any]:
    """Load configuration from JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Parsed configuration dictionary
        
    Raises:
        MCPConfigError: If file cannot be read or parsed
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except (IOError, json.JSONDecodeError) as e:
        raise MCPConfigError(
            f"Failed to load configuration from {config_path}: {e}",
            config_path=str(config_path)
        ) from e


def _validate_mcp_config(config: Dict[str, Any]) -> None:
    """Validate MCP configuration structure.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        MCPConfigError: If configuration is invalid
    """
    # Check for required top-level structure
    if not isinstance(config, dict):
        raise MCPConfigError("Configuration must be a JSON object")
    

    servers = config
    if not isinstance(servers, dict):
        raise MCPConfigError("'config' must be an object")
    
    if not servers:
        raise MCPConfigError("'config' cannot be empty")
    
    # Validate each server configuration
    for server_name, server_config in servers.items():
        _validate_server_config(server_name, server_config)


def _validate_server_config(server_name: str, server_config: Dict[str, Any]) -> None:
    """Validate individual server configuration.
    
    Args:
        server_name: Name of the server
        server_config: Server configuration dictionary
        
    Raises:
        MCPConfigError: If server configuration is invalid
    """
    if not isinstance(server_config, dict):
        raise MCPConfigError(f"Server '{server_name}' configuration must be an object")
    
    # Required fields
    required_fields = ["command", "args"]
    for field in required_fields:
        if field not in server_config:
            raise MCPConfigError(f"Server '{server_name}' missing required field: {field}")
    
    # Validate command
    command = server_config["command"]
    if not isinstance(command, str) or not command.strip():
        raise MCPConfigError(f"Server '{server_name}' command must be a non-empty string")
    
    # Validate args
    args = server_config["args"]
    if not isinstance(args, list):
        raise MCPConfigError(f"Server '{server_name}' args must be a list")
    
    # Validate environment variables (if present)
    if "env" in server_config:
        env = server_config["env"]
        if not isinstance(env, dict):
            raise MCPConfigError(f"Server '{server_name}' env must be an object")
        
        # Check that all env values are strings
        for key, value in env.items():
            if not isinstance(value, str):
                raise MCPConfigError(
                    f"Server '{server_name}' env variable '{key}' must be a string"
                )


def transform_config_for_mcp_client(config: Dict[str, Any]) -> Dict[str, Any]:
    """Transform configuration to MCP client format.
    
    Args:
        config: Raw configuration dictionary
        
    Returns:
        Configuration transformed for MCP client usage
    """
    # For now, return as-is since langchain-mcp-adapters expects this format
    # Future: Add any necessary transformations here
    return config


def _resolve_relative_paths(config: Dict[str, Any], config_dir: Path) -> Dict[str, Any]:
    """Resolve relative paths in configuration relative to config file directory.
    
    Args:
        config: Configuration dictionary
        config_dir: Directory containing the config file
        
    Returns:
        Configuration with relative paths resolved
    """
    if not isinstance(config, dict):
        return config
    
    result = {}
    
    for server_name, server_config in config.items():
        if isinstance(server_config, dict):
            resolved_server_config = server_config.copy()
            
            # Resolve relative paths in args
            if "args" in resolved_server_config and isinstance(resolved_server_config["args"], list):
                resolved_args = []
                for arg in resolved_server_config["args"]:
                    if isinstance(arg, str):
                        # Check if this looks like a relative path (contains / or \ but doesn't start with /)
                        if ("/" in arg or "\\" in arg) and not os.path.isabs(arg):
                            # Resolve relative to config directory
                            resolved_path = config_dir / arg
                            resolved_args.append(str(resolved_path.resolve()))
                        else:
                            resolved_args.append(arg)
                    else:
                        resolved_args.append(arg)
                resolved_server_config["args"] = resolved_args
            
            # Resolve relative paths in command if it looks like a path
            if "command" in resolved_server_config:
                command = resolved_server_config["command"]
                if isinstance(command, str) and ("/" in command or "\\" in command) and not os.path.isabs(command):
                    resolved_path = config_dir / command
                    resolved_server_config["command"] = str(resolved_path.resolve())
            
            result[server_name] = resolved_server_config
        else:
            result[server_name] = server_config
    
    return result


def substitute_environment_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """Substitute environment variables in configuration.
    
    Args:
        config: Configuration dictionary with potential env var references
        
    Returns:
        Configuration with environment variables substituted
    """
    if not isinstance(config, dict):
        return config
    
    result = {}
    
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = substitute_environment_variables(value)
        elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            # Extract environment variable name
            env_var = value[2:-1]
            default_value = ""
            
            # Support default values: ${VAR:default}
            if ":" in env_var:
                env_var, default_value = env_var.split(":", 1)
            
            result[key] = os.getenv(env_var, default_value)
        else:
            result[key] = value
    
    return result
