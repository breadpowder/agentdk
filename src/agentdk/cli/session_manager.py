"""Session management for AgentDK CLI using memory component."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click


class SessionManager:
    """Manages session persistence for CLI interactions."""
    
    def __init__(self, agent_name: str, session_dir: Optional[Path] = None):
        self.agent_name = agent_name
        self.session_dir = session_dir or Path.home() / ".agentdk" / "sessions"
        self.session_file = self.session_dir / f"{agent_name}_session.json"
        self.current_session: Dict[str, Any] = {}
        
        # Ensure session directory exists
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    async def start_new_session(self):
        """Start a new session, clearing any previous session data."""
        self.current_session = {
            "agent_name": self.agent_name,
            "created_at": datetime.now().isoformat(),
            "interactions": []
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
        if not self.session_file.exists():
            click.echo(f"No previous session found for {self.agent_name}")
            await self.start_new_session()
            return False
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                self.current_session = json.load(f)
            
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
            
            return True
            
        except Exception as e:
            click.secho(f"Error loading session: {e}", fg="yellow")
            await self.start_new_session()
            return False
    
    async def save_interaction(self, user_input: str, agent_response: str):
        """Save a single interaction to the current session."""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response
        }
        
        self.current_session["interactions"].append(interaction)
        
        # Save to file immediately for persistence
        await self._save_session_to_file()
    
    async def _save_session_to_file(self):
        """Save current session data to file."""
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_session, f, indent=2, ensure_ascii=False)
        except Exception as e:
            click.secho(f"Warning: Could not save session: {e}", fg="yellow")
    
    async def close(self):
        """Close the session and perform final cleanup."""
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
        return self.current_session.get("interactions", [])
    
    def clear_session(self):
        """Clear the current session and remove session file."""
        if self.session_file.exists():
            self.session_file.unlink()
        
        self.current_session = {
            "agent_name": self.agent_name,
            "created_at": datetime.now().isoformat(),
            "interactions": []
        }
        
        click.echo(f"Session cleared for {self.agent_name}")