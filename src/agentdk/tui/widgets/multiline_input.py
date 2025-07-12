"""Multi-line input widget for AgentDK TUI."""

from typing import Optional, List, Callable
from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import TextArea
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult

from agentdk.core.logging_config import get_logger
from agentdk.cli.main import GlobalCLIHistory

logger = get_logger(__name__)


class MultilineInput(Widget):
    """A multi-line input widget with history support and enhanced editing."""
    
    DEFAULT_CSS = """
    MultilineInput {
        height: 8;
        border: round cyan;
    }
    
    MultilineInput:focus-within {
        border: round green;
    }
    
    MultilineInput TextArea {
        background: transparent;
        border: none;
    }
    
    MultilineInput TextArea:focus {
        background: transparent;
        border: none;
    }
    
    MultilineInput .status-bar {
        height: 1;
        background: grey;
        padding: 0 1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+enter", "submit", "Submit", show=True),
        Binding("ctrl+c", "cancel", "Cancel", show=True),
        Binding("ctrl+k", "clear", "Clear", show=True),
        Binding("up", "history_previous", "Previous", show=False),
        Binding("down", "history_next", "Next", show=False),
        Binding("ctrl+up", "history_previous", "Previous", show=False),
        Binding("ctrl+down", "history_next", "Next", show=False),
    ]
    
    class Submitted(Message):
        """Message sent when input is submitted."""
        
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text
    
    class Cancelled(Message):
        """Message sent when input is cancelled."""
        pass
    
    # Reactive attributes
    placeholder: reactive[str] = reactive("Enter your message...")
    show_status: reactive[bool] = reactive(True)
    
    def __init__(
        self,
        placeholder: str = "Enter your message...",
        show_status: bool = True,
        history_manager: Optional[GlobalCLIHistory] = None,
        **kwargs
    ):
        """Initialize the multi-line input widget.
        
        Args:
            placeholder: Placeholder text to show when empty
            show_status: Whether to show status bar
            history_manager: Optional history manager for command history
            **kwargs: Additional arguments passed to Widget
        """
        super().__init__(**kwargs)
        
        self.placeholder = placeholder
        self.show_status = show_status
        self.history_manager = history_manager or GlobalCLIHistory()
        
        # Internal state
        self._current_history_index = len(self.history_manager.commands)
        self._temp_text = ""  # Store current text when navigating history
        
        logger.debug(f"MultilineInput initialized with {len(self.history_manager.commands)} history items")
    
    def compose(self) -> ComposeResult:
        """Compose the input widget."""
        with Vertical():
            # Main text area
            yield TextArea(
                text="",
                show_line_numbers=False,
                tab_behavior="indent",
                id="input_area"
            )
            
            # Status bar (if enabled)
            if self.show_status:
                from textual.widgets import Static
                yield Static(
                    "Ctrl+Enter: Submit | Ctrl+C: Cancel | ↑/↓: History | Ctrl+K: Clear",
                    classes="status-bar"
                )
    
    def on_mount(self) -> None:
        """Handle widget mount."""
        self.border_title = "Enter your query"
        
        # Focus the text area
        text_area = self.query_one("#input_area", TextArea)
        text_area.focus()
        
        logger.debug("MultilineInput mounted and focused")
    
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes."""
        # Reset history navigation when user types
        if event.text_area.text != self._temp_text:
            self._current_history_index = len(self.history_manager.commands)
            self._temp_text = ""
    
    def action_submit(self) -> None:
        """Submit the current input."""
        text_area = self.query_one("#input_area", TextArea)
        text = text_area.text.strip()
        
        if not text:
            return
        
        logger.debug(f"Submitting input: {text[:50]}...")
        
        # Add to history
        self.history_manager.add_command(text)
        
        # Clear the input
        text_area.text = ""
        self._current_history_index = len(self.history_manager.commands)
        self._temp_text = ""
        
        # Send message
        self.post_message(self.Submitted(text))
    
    def action_cancel(self) -> None:
        """Cancel the current input."""
        text_area = self.query_one("#input_area", TextArea)
        text_area.text = ""
        self._current_history_index = len(self.history_manager.commands)
        self._temp_text = ""
        
        logger.debug("Input cancelled")
        self.post_message(self.Cancelled())
    
    def action_clear(self) -> None:
        """Clear the current input."""
        text_area = self.query_one("#input_area", TextArea)
        text_area.text = ""
        self._current_history_index = len(self.history_manager.commands)
        self._temp_text = ""
        
        logger.debug("Input cleared")
    
    def action_history_previous(self) -> None:
        """Navigate to previous command in history."""
        if not self.history_manager.commands:
            return
        
        text_area = self.query_one("#input_area", TextArea)
        
        # Store current text if at the end of history
        if self._current_history_index >= len(self.history_manager.commands):
            self._temp_text = text_area.text
        
        # Navigate to previous command
        if self._current_history_index > 0:
            self._current_history_index -= 1
            text_area.text = self.history_manager.commands[self._current_history_index]
            text_area.move_cursor_to_end()
            
            logger.debug(f"History: moved to index {self._current_history_index}")
    
    def action_history_next(self) -> None:
        """Navigate to next command in history."""
        if not self.history_manager.commands:
            return
        
        text_area = self.query_one("#input_area", TextArea)
        
        # Navigate to next command
        if self._current_history_index < len(self.history_manager.commands) - 1:
            self._current_history_index += 1
            text_area.text = self.history_manager.commands[self._current_history_index]
            text_area.move_cursor_to_end()
            
            logger.debug(f"History: moved to index {self._current_history_index}")
        elif self._current_history_index == len(self.history_manager.commands) - 1:
            # Move to end of history (restore temp text)
            self._current_history_index = len(self.history_manager.commands)
            text_area.text = self._temp_text
            text_area.move_cursor_to_end()
            
            logger.debug("History: moved to end")
    
    def focus(self, scroll_visible: bool = True) -> None:
        """Focus the input widget."""
        super().focus(scroll_visible)
        
        # Focus the text area
        text_area = self.query_one("#input_area", TextArea)
        text_area.focus()
    
    def clear(self) -> None:
        """Clear the input text."""
        self.action_clear()
    
    def get_text(self) -> str:
        """Get the current input text."""
        text_area = self.query_one("#input_area", TextArea)
        return text_area.text
    
    def set_text(self, text: str) -> None:
        """Set the input text."""
        text_area = self.query_one("#input_area", TextArea)
        text_area.text = text
        text_area.move_cursor_to_end()
    
    def append_text(self, text: str) -> None:
        """Append text to the current input."""
        text_area = self.query_one("#input_area", TextArea)
        current_text = text_area.text
        if current_text and not current_text.endswith('\n'):
            text = '\n' + text
        text_area.text = current_text + text
        text_area.move_cursor_to_end()