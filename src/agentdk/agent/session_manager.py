"""Session management for AgentDK agents using memory component.

This module provides session management capabilities for parent agents only.
Child agents created through supervisor patterns do not manage sessions.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click


class SessionManager:
    """Manages session persistence for parent agent interactions."""
    
    def __init__(self, agent_name: str, is_parent_agent: bool = False, session_dir: Optional[Path] = None):
        """Initialize SessionManager.
        
        Args:
            agent_name: Name of the agent
            is_parent_agent: Whether this agent is a parent agent (manages sessions)
            session_dir: Optional directory for session files
        """
        self.agent_name = agent_name
        self.is_parent_agent = is_parent_agent
        self.session_dir = session_dir or Path.home() / ".agentdk" / "sessions"
        self.current_session: Dict[str, Any] = {}
        
        # Only create session infrastructure for parent agents
        if self.is_parent_agent:
            self.session_file = self.session_dir / f"{agent_name}_session.json"
            self.session_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.session_file = None
        
        # Format version for compatibility
        self.format_version = "1.0"
    
    def should_manage_session(self) -> bool:
        """Check if this agent should manage sessions.
        
        Returns:
            bool: True if this is a parent agent that should manage sessions
        """
        return self.is_parent_agent and self.session_file is not None
    
    async def start_new_session(self):
        """Start a new session, clearing any previous session data."""
        if not self.should_manage_session():
            return
        
        self.current_session = {
            "agent_name": self.agent_name,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "format_version": self.format_version,
            "interactions": [],
            "memory_state": {}
        }
        
        # Remove old session file if it exists
        if self.session_file.exists():
            self.session_file.unlink()
        
        click.echo(f"Started new session for {self.agent_name}")
    
    async def load_session(self) -> bool:
        """Load previous session if it exists.
        
        Returns:
            bool: True if session was loaded, False if no previous session exists
        """
        if not self.should_manage_session():
            return False
        
        if not self.session_file.exists():
            click.echo(f"No previous session found for {self.agent_name}")
            await self.start_new_session()
            return False
        
        # Validate session format first
        if not self._validate_session_format():
            click.secho("Session file format outdated or corrupted, starting fresh", fg="yellow")
            await self._backup_corrupted_session()
            await self.start_new_session()
            return False
        
        try:
            # Load and validate session data
            self.current_session = self._load_and_validate_session()
            
            # Display previous interactions
            interactions = self.current_session.get("interactions", [])
            if interactions:
                click.echo(f"\\nResuming session with {len(interactions)} previous interactions:\\n")
                
                # Show last few interactions for context
                recent_interactions = interactions[-5:] if len(interactions) > 5 else interactions
                for interaction in recent_interactions:
                    click.echo(f"[user]: {interaction['user_input']}")
                    click.echo(f"[{self.agent_name}]: {interaction['agent_response']}")
                
                if len(interactions) > 5:
                    click.echo(f"... ({len(interactions) - 5} earlier interactions)")
                click.echo("")
                
                # Show memory state info if available
                memory_state = self.current_session.get("memory_state", {})
                if memory_state:
                    click.echo(f"Memory state restored (format: {self.current_session.get('format_version', 'unknown')})")
            
            return True
            
        except (json.JSONDecodeError, KeyError) as e:
            click.secho(f"Session file corrupted: {e}, starting fresh", fg="yellow")
            await self._backup_corrupted_session()
            await self.start_new_session()
            return False
        except Exception as e:
            click.secho(f"Error loading session: {e}", fg="yellow")
            await self.start_new_session()
            return False
    
    async def save_interaction(self, user_input: str, agent_response: str, memory_state: Optional[Dict] = None):
        """Save a single interaction to the current session."""
        if not self.should_manage_session():
            return
        
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response
        }
        
        self.current_session["interactions"].append(interaction)
        self.current_session["last_updated"] = datetime.now().isoformat()
        
        # Update memory state if provided
        if memory_state:
            self.current_session["memory_state"] = memory_state
        
        # Save to file immediately for persistence
        await self._save_session_to_file()
    
    async def _save_session_to_file(self):
        """Save current session data to file."""
        if not self.should_manage_session():
            return
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_session, f, indent=2, ensure_ascii=False)
        except Exception as e:
            click.secho(f"Warning: Could not save session: {e}", fg="yellow")
    
    async def close(self):
        """Close the session and perform final cleanup."""
        if not self.should_manage_session():
            return
        
        # Final save
        await self._save_session_to_file()
        
        # Display session summary
        interactions_count = len(self.current_session.get("interactions", []))
        if interactions_count > 0:
            click.echo(f"Session saved with {interactions_count} interactions.")
            click.echo(f"Resume with: agentdk run <agent_path> --resume")
        
    def get_session_context(self) -> List[Dict[str, str]]:
        """Get session context for memory-aware agents.
        
        Returns:
            List of previous interactions that can be used for context
        """
        if not self.should_manage_session():
            return []
        
        return self.current_session.get("interactions", [])
    
    def clear_session(self):
        """Clear the current session and remove session file."""
        if not self.should_manage_session():
            return
        
        if self.session_file.exists():
            self.session_file.unlink()
        
        self.current_session = {
            "agent_name": self.agent_name,
            "created_at": datetime.now().isoformat(),
            "interactions": []
        }
        
        click.echo(f"Session cleared for {self.agent_name}")
    
    def _validate_session_format(self) -> bool:
        """Validate session file format and version compatibility.
        
        Returns:
            bool: True if format is valid and compatible
        """
        if not self.should_manage_session() or not self.session_file.exists():
            return False
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check required fields
            required_fields = ["agent_name", "created_at", "interactions"]
            if not all(field in data for field in required_fields):
                return False
            
            # Check format version (if present)
            file_version = data.get("format_version", "0.9")  # Default to old version
            if file_version != self.format_version:
                # Could add version migration logic here
                return file_version in ["0.9", "1.0"]  # Support old and new versions
            
            return True
            
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return False
    
    def _load_and_validate_session(self) -> Dict[str, Any]:
        """Load and validate session data with error handling.
        
        Returns:
            Dict containing session data
            
        Raises:
            json.JSONDecodeError: If JSON is invalid
            KeyError: If required fields are missing
            FileNotFoundError: If session file doesn't exist
        """
        with open(self.session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Migrate old format to new format if needed
        if "format_version" not in data:
            data["format_version"] = "0.9"
            data["last_updated"] = data.get("created_at", datetime.now().isoformat())
            data["memory_state"] = {}
        
        return data
    
    async def _backup_corrupted_session(self):
        """Backup a corrupted session file for debugging."""
        if not self.should_manage_session() or not self.session_file.exists():
            return
        
        backup_file = self.session_dir / f"{self.agent_name}_session_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            import shutil
            shutil.copy2(self.session_file, backup_file)
            click.echo(f"Corrupted session backed up to: {backup_file}")
        except Exception as e:
            click.secho(f"Could not backup corrupted session: {e}", fg="yellow")
    
    def get_memory_state(self) -> Dict[str, Any]:
        """Get memory state from current session for agent restoration.
        
        Returns:
            Dictionary containing memory state data
        """
        if not self.should_manage_session():
            return {}
        
        return self.current_session.get("memory_state", {})
    
    def save_memory_state(self, memory_state: Dict[str, Any]):
        """Save memory state from agent to current session.
        
        Args:
            memory_state: Dictionary containing memory state data
        """
        if not self.should_manage_session():
            return
        
        self.current_session["memory_state"] = memory_state
        self.current_session["last_updated"] = datetime.now().isoformat()
    
    def has_previous_session(self) -> bool:
        """Check if a previous session exists and is valid.
        
        Returns:
            bool: True if valid previous session exists
        """
        return self._validate_session_format()
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information for status display.
        
        Returns:
            Dictionary containing session info
        """
        if not self.should_manage_session():
            return {"exists": False, "agent_name": self.agent_name, "is_parent_agent": False}
        
        if not self.session_file.exists():
            return {"exists": False, "agent_name": self.agent_name, "is_parent_agent": True}
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                "exists": True,
                "agent_name": data.get("agent_name", self.agent_name),
                "created_at": data.get("created_at"),
                "last_updated": data.get("last_updated"),
                "format_version": data.get("format_version", "unknown"),
                "interaction_count": len(data.get("interactions", [])),
                "has_memory_state": bool(data.get("memory_state")),
                "is_parent_agent": True
            }
        except Exception as e:
            return {
                "exists": True,
                "agent_name": self.agent_name,
                "error": str(e),
                "corrupted": True,
                "is_parent_agent": True
            }