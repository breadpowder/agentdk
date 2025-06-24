"""Tests for agentdk.core.mcp_load module."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from agentdk.core.mcp_load import (
    get_mcp_config, _validate_mcp_config, _load_config_file,
    _get_config_search_paths, transform_config_for_mcp_client, _resolve_relative_paths
)
from agentdk.exceptions import MCPConfigError


def test_validate_mcp_config_valid():
    """Test _validate_mcp_config with valid configuration."""
    valid_config = {
        "mysql": {
            "command": "uv",
            "args": ["--directory", "/path/to/server", "run", "mysql_mcp_server"],
            "env": {
                "MYSQL_HOST": "localhost",
                "MYSQL_PORT": "3306"
            }
        }
    }
    
    # Should not raise any exception
    _validate_mcp_config(valid_config)


def test_validate_mcp_config_invalid():
    """Test _validate_mcp_config with various invalid configurations."""
    # Test non-dict config
    with pytest.raises(MCPConfigError, match="Configuration must be a JSON object"):
        _validate_mcp_config("not a dict")
    
    # Test empty config
    with pytest.raises(MCPConfigError, match="'config' cannot be empty"):
        _validate_mcp_config({})
    
    # Test missing command
    invalid_config = {
        "server1": {
            "args": ["test"]
        }
    }
    with pytest.raises(MCPConfigError, match="missing required field: command"):
        _validate_mcp_config(invalid_config)
    
    # Test invalid args type
    invalid_config = {
        "server1": {
            "command": "test",
            "args": "not a list"
        }
    }
    with pytest.raises(MCPConfigError, match="args must be a list"):
        _validate_mcp_config(invalid_config)


def test_load_config_file_success():
    """Test _load_config_file successfully loads valid JSON."""
    config_data = {"server": {"command": "test", "args": []}}
    json_content = json.dumps(config_data)
    
    with patch('builtins.open', mock_open(read_data=json_content)):
        result = _load_config_file(Path("test_config.json"))
        assert result == config_data


def test_load_config_file_invalid():
    """Test _load_config_file handles invalid JSON and file errors."""
    # Test invalid JSON
    with patch('builtins.open', mock_open(read_data="invalid json")):
        with pytest.raises(MCPConfigError, match="Failed to load configuration"):
            _load_config_file(Path("test_config.json"))
    
    # Test file not found
    with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
        with pytest.raises(MCPConfigError, match="Failed to load configuration"):
            _load_config_file(Path("nonexistent.json"))


def test_get_config_search_paths():
    """Test _get_config_search_paths returns appropriate search paths."""
    # Create mock agent instance
    mock_agent = Mock()
    mock_agent._mcp_config_path = "custom/path.json"
    mock_agent.__class__ = Mock()
    
    with patch('inspect.getfile', return_value="/agent/dir/agent.py"):
        paths = _get_config_search_paths(mock_agent)
        
        # Should include explicit path first
        assert Path("custom/path.json") in paths
        
        # Should include agent directory
        assert Path("/agent/dir/mcp_config.json") in paths
        
        # Should include current directory
        assert Path.cwd() / "mcp_config.json" in paths 


def test_resolve_relative_paths() -> None:
    """Test that relative paths in configuration are resolved relative to config directory."""
    config = {
        "mysql": {
            "command": "uv",
            "args": ["--directory", "../mysql_server", "run", "server"],
            "env": {"HOST": "localhost"},
            "transport": "stdio"
        },
        "postgres": {
            "command": "/usr/bin/postgres",  # absolute path should not change
            "args": ["--config", "config.conf"],  # non-path arg should not change
            "env": {"PORT": "5432"}
        }
    }
    
    config_dir = Path("/home/user/project/configs")
    resolved = _resolve_relative_paths(config, config_dir)
    
    # Relative path should be resolved
    expected_mysql_path = str((config_dir / "../mysql_server").resolve())
    assert resolved["mysql"]["args"][1] == expected_mysql_path
    
    # Other args should remain unchanged
    assert resolved["mysql"]["args"][0] == "--directory"
    assert resolved["mysql"]["args"][2] == "run"
    assert resolved["mysql"]["args"][3] == "server"
    
    # Absolute command should remain unchanged
    assert resolved["postgres"]["command"] == "/usr/bin/postgres"
    
    # Non-path args should remain unchanged
    assert resolved["postgres"]["args"] == ["--config", "config.conf"]
    
    # Environment variables should remain unchanged
    assert resolved["mysql"]["env"] == {"HOST": "localhost"}
    assert resolved["postgres"]["env"] == {"PORT": "5432"} 