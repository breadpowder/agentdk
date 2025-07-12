"""Main Textual application for AgentDK TUI."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.driver import Driver

from agentdk.core.logging_config import get_logger
from .screens.chat_screen import ChatScreen
from .themes.agentdk_theme import AGENTDK_THEME

logger = get_logger(__name__)


class AgentDKApp(App):
    """Main AgentDK TUI application."""
    
    CSS_PATH = None  # We'll define styles programmatically
    TITLE = "AgentDK - Intelligent Agent Interface"
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Exit", show=True),
        Binding("ctrl+q", "quit", "Exit", show=False),
        Binding("f1", "help", "Help", show=True),
    ]
    
    def __init__(
        self,
        agent,
        agent_name: str = "agent",
        resume: bool = False,
        **kwargs
    ):
        """Initialize the AgentDK TUI application.
        
        Args:
            agent: The agent instance to interact with
            agent_name: Name of the agent for session management
            resume: Whether to resume from previous session
            **kwargs: Additional arguments passed to App
        """
        super().__init__(**kwargs)
        
        self.agent = agent
        self.agent_name = agent_name
        self.resume = resume
        
        # Theme will be applied via CSS and design tokens
        
        logger.info(f"Initialized AgentDK TUI for agent: {agent_name}")
    
    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield ChatScreen(
            agent=self.agent,
            agent_name=self.agent_name,
            resume=self.resume,
            id="chat_screen"
        )
    
    def on_mount(self) -> None:
        """Handle application mount."""
        logger.info("AgentDK TUI mounted successfully")
        
        # Set initial focus to chat screen
        self.query_one("#chat_screen").focus()
    
    def action_help(self) -> None:
        """Show help information."""
        self.bell()
        # TODO: Implement help screen in future
        logger.info("Help requested - not implemented yet")
    
    def action_quit(self) -> None:
        """Handle quit action."""
        logger.info("Quit requested - shutting down gracefully")
        
        # Let the chat screen handle cleanup
        chat_screen = self.query_one("#chat_screen")
        if hasattr(chat_screen, 'cleanup'):
            chat_screen.cleanup()
        
        self.exit()
    
    def on_key(self, event) -> None:
        """Handle global key events."""
        # Handle global key events
        if event.key == "ctrl+c":
            self.action_quit()
            event.prevent_default()
            event.stop()


def run_tui_app(
    agent, 
    agent_name: str = "agent", 
    resume: bool = False,
    driver: Optional[Driver] = None
) -> None:
    """Run the AgentDK TUI application.
    
    Args:
        agent: The agent instance to interact with
        agent_name: Name of the agent for session management
        resume: Whether to resume from previous session
        driver: Optional Textual driver to use
    """
    try:
        app = AgentDKApp(
            agent=agent,
            agent_name=agent_name,
            resume=resume
        )
        
        logger.info("Starting AgentDK TUI application")
        app.run()
        
    except KeyboardInterrupt:
        logger.info("TUI application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"TUI application error: {e}")
        sys.exit(1)
    finally:
        logger.info("TUI application shutdown complete")