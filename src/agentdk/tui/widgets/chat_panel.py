"""Chat panel widget for displaying conversations."""

from typing import List, Dict, Any
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static, RichLog
from textual.app import ComposeResult
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown

from agentdk.core.logging_config import get_logger

logger = get_logger(__name__)


class ChatPanel(Widget):
    """A panel for displaying chat conversations with rich formatting."""
    
    DEFAULT_CSS = """
    ChatPanel {
        border: round blue;
        height: 1fr;
        min-height: 10;
    }
    
    ChatPanel RichLog {
        background: transparent;
        border: none;
    }
    """
    
    def __init__(self, **kwargs):
        """Initialize the chat panel."""
        super().__init__(**kwargs)
        
        self._conversation_history: List[Dict[str, Any]] = []
        
        logger.debug("ChatPanel initialized")
    
    def compose(self) -> ComposeResult:
        """Compose the chat panel."""
        yield RichLog(
            markup=True,
            highlight=True,
            auto_scroll=True,
            wrap=True,
            id="chat_log"
        )
    
    def on_mount(self) -> None:
        """Handle widget mount."""
        self.border_title = "Conversation"
        logger.debug("ChatPanel mounted")
    
    def add_message(
        self,
        content: str,
        sender: str = "user",
        message_type: str = "normal",
        **kwargs
    ) -> None:
        """Add a message to the chat panel.
        
        Args:
            content: Message content
            sender: Message sender ('user', 'agent', 'system')
            message_type: Type of message ('normal', 'error', 'info', 'warning')
            **kwargs: Additional message metadata
        """
        # Store in conversation history
        message = {
            "content": content,
            "sender": sender,
            "message_type": message_type,
            **kwargs
        }
        self._conversation_history.append(message)
        
        # Get the rich log widget
        rich_log = self.query_one("#chat_log", RichLog)
        
        # Format the message based on sender and type
        formatted_message = self._format_message(content, sender, message_type)
        
        # Add to the log
        rich_log.write(formatted_message)
        
        logger.debug(f"Added message from {sender}: {content[:50]}...")
    
    def _format_message(self, content: str, sender: str, message_type: str) -> Any:
        """Format a message for display.
        
        Args:
            content: Message content
            sender: Message sender
            message_type: Message type
            
        Returns:
            Formatted message for RichLog
        """
        # Color mapping for different senders
        sender_colors = {
            "user": "bright_blue",
            "agent": "green", 
            "system": "yellow",
            "error": "red",
            "info": "cyan",
            "warning": "yellow"
        }
        
        # Get color for sender
        color = sender_colors.get(sender, "white")
        
        # Format sender label
        if sender == "user":
            sender_label = "You"
        elif sender == "agent":
            sender_label = "Agent"
        elif sender == "system":
            sender_label = "System"
        else:
            sender_label = sender.title()
        
        # Create the formatted message
        if message_type == "error":
            # Error messages in red panel
            panel = Panel(
                content,
                title=f"[red]❌ {sender_label}[/red]",
                border_style="red",
                padding=(0, 1)
            )
            return panel
        elif message_type == "warning":
            # Warning messages in yellow panel
            panel = Panel(
                content,
                title=f"[yellow]⚠️  {sender_label}[/yellow]",
                border_style="yellow",
                padding=(0, 1)
            )
            return panel
        elif message_type == "info":
            # Info messages in cyan
            panel = Panel(
                content,
                title=f"[cyan]ℹ️  {sender_label}[/cyan]",
                border_style="cyan",
                padding=(0, 1)
            )
            return panel
        else:
            # Normal messages
            if sender == "user":
                # User messages with blue styling
                panel = Panel(
                    content,
                    title=f"[bright_blue]👤 {sender_label}[/bright_blue]",
                    border_style="bright_blue",
                    padding=(0, 1)
                )
                return panel
            elif sender == "agent":
                # Agent messages with green styling and markdown support
                try:
                    # Try to render as markdown for better formatting
                    markdown_content = Markdown(content)
                    panel = Panel(
                        markdown_content,
                        title=f"[green]🤖 {sender_label}[/green]",
                        border_style="green",
                        padding=(0, 1)
                    )
                    return panel
                except Exception:
                    # Fallback to plain text if markdown fails
                    panel = Panel(
                        content,
                        title=f"[green]🤖 {sender_label}[/green]",
                        border_style="green",
                        padding=(0, 1)
                    )
                    return panel
            else:
                # System or other messages
                panel = Panel(
                    content,
                    title=f"[{color}]📋 {sender_label}[/{color}]",
                    border_style=color,
                    padding=(0, 1)
                )
                return panel
    
    def clear(self) -> None:
        """Clear the chat panel."""
        rich_log = self.query_one("#chat_log", RichLog)
        rich_log.clear()
        self._conversation_history.clear()
        
        logger.debug("ChatPanel cleared")
    
    def add_system_message(self, message: str) -> None:
        """Add a system message."""
        self.add_message(message, sender="system", message_type="info")
    
    def add_error_message(self, message: str) -> None:
        """Add an error message."""
        self.add_message(message, sender="system", message_type="error")
    
    def add_warning_message(self, message: str) -> None:
        """Add a warning message."""
        self.add_message(message, sender="system", message_type="warning")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        return self._conversation_history.copy()
    
    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the chat log."""
        rich_log = self.query_one("#chat_log", RichLog)
        rich_log.scroll_end()
    
    def export_conversation(self, format: str = "text") -> str:
        """Export the conversation in the specified format.
        
        Args:
            format: Export format ('text', 'markdown', 'json')
            
        Returns:
            Exported conversation as string
        """
        if format == "json":
            import json
            return json.dumps(self._conversation_history, indent=2)
        elif format == "markdown":
            lines = []
            for msg in self._conversation_history:
                sender = msg["sender"].title()
                content = msg["content"]
                lines.append(f"## {sender}\n\n{content}\n")
            return "\n".join(lines)
        else:  # text format
            lines = []
            for msg in self._conversation_history:
                sender = msg["sender"].title()
                content = msg["content"]
                lines.append(f"{sender}: {content}")
            return "\n\n".join(lines)