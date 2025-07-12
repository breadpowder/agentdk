"""Chat screen for AgentDK TUI."""

import asyncio
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header
from textual.worker import Worker

from agentdk.core.logging_config import get_logger
from agentdk.agent.session_manager import SessionManager
from agentdk.cli.main import GlobalCLIHistory
from ..widgets.multiline_input import MultilineInput
from ..widgets.chat_panel import ChatPanel

logger = get_logger(__name__)


class ChatScreen(Screen):
    """Main chat screen for agent interaction."""
    
    CSS = """
    ChatScreen Vertical {
        height: 100%;
    }
    
    ChatScreen .chat-container {
        height: 1fr;
        margin: 1;
    }
    
    ChatScreen .input-container {
        height: auto;
        margin: 1;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+r", "refresh", "Refresh", show=True),
        Binding("ctrl+s", "save_session", "Save Session", show=True),
        Binding("ctrl+e", "export_chat", "Export Chat", show=False),
        Binding("f2", "toggle_debug", "Debug", show=False),
    ]
    
    def __init__(
        self,
        agent,
        agent_name: str = "agent",
        resume: bool = False,
        **kwargs
    ):
        """Initialize the chat screen.
        
        Args:
            agent: The agent instance to interact with
            agent_name: Name of the agent for session management
            resume: Whether to resume from previous session
            **kwargs: Additional arguments passed to Screen
        """
        super().__init__(**kwargs)
        
        self.agent = agent
        self.agent_name = agent_name
        self.resume = resume
        
        # Initialize session manager
        self.session_manager = SessionManager(agent_name)
        
        # Initialize history manager
        self.history_manager = GlobalCLIHistory()
        
        # Track current processing
        self._processing = False
        self._current_worker: Optional[Worker] = None
        
        logger.info(f"ChatScreen initialized for agent: {agent_name}")
    
    def compose(self) -> ComposeResult:
        """Compose the chat screen layout."""
        from textual.widgets import Static
        
        yield Header(show_clock=True)
        
        with Vertical():
            # Temporary: Use simple Static widget to test basic rendering
            yield Static("🚀 AgentDK TUI - Chat Interface", classes="chat-container", id="chat_panel")
            yield Static("📝 Input Area (Type your message here)", classes="input-container", id="input_widget")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Handle screen mount."""
        self.title = f"AgentDK - {self.agent_name}"
        logger.info(f"ChatScreen mounted with title: {self.title}")
    
    async def _async_mount_setup(self) -> None:
        """Handle async mount setup."""
        chat_panel = self.query_one("#chat_panel", ChatPanel)
        
        try:
            # Handle session resumption
            if self.resume:
                logger.info("Resume mode enabled - loading previous session")
                chat_panel.add_system_message("🔄 Loading previous session...")
                
                session_loaded = await self.session_manager.load_session()
                
                if session_loaded:
                    # Restore agent memory if supported
                    if hasattr(self.agent, 'restore_from_session'):
                        session_context = self.session_manager.get_session_context()
                        if session_context:
                            success = self.agent.restore_from_session(session_context)
                            if success:
                                chat_panel.add_system_message("✅ Session restored successfully")
                                logger.info("Agent memory restored from session")
                            else:
                                chat_panel.add_warning_message("⚠️ Failed to restore agent memory")
                                logger.warning("Failed to restore agent memory from session")
                        else:
                            chat_panel.add_warning_message("⚠️ No session context found")
                    else:
                        chat_panel.add_system_message("✅ Session loaded (agent does not support memory restoration)")
                else:
                    chat_panel.add_warning_message("⚠️ No previous session found, starting fresh")
            else:
                logger.debug("Starting with fresh memory")
                await self.session_manager.start_new_session()
                
                # Clear agent memory if supported
                if hasattr(self.agent, 'memory') and self.agent.memory:
                    try:
                        working_memory = getattr(self.agent.memory, 'working_memory', None)
                        if working_memory and hasattr(working_memory, 'clear'):
                            working_memory.clear()
                            logger.debug("Agent working memory cleared for fresh start")
                    except Exception as e:
                        logger.warning(f"Could not clear agent memory: {e}")
                
                chat_panel.add_system_message("🚀 Welcome to AgentDK! Ready to assist you.")
            
            # Show usage instructions
            chat_panel.add_system_message(
                "💡 **Usage Tips:**\n"
                "• Type your message in the input box below\n"
                "• Press **Ctrl+Enter** to send your message\n"
                "• Use **↑/↓** arrow keys to navigate command history\n"
                "• Press **Ctrl+C** to quit\n"
                "• Press **Ctrl+S** to save current session"
            )
            
        except Exception as e:
            logger.error(f"Error during screen mount: {e}")
            chat_panel.add_error_message(f"Error during initialization: {str(e)}")
    
    async def on_multiline_input_submitted(self, event: MultilineInput.Submitted) -> None:
        """Handle input submission."""
        if self._processing:
            return
        
        user_input = event.text.strip()
        if not user_input:
            return
        
        chat_panel = self.query_one("#chat_panel", ChatPanel)
        input_widget = self.query_one("#input_widget", MultilineInput)
        
        # Add user message to chat
        chat_panel.add_message(user_input, sender="user")
        
        # Show processing indicator
        self._processing = True
        chat_panel.add_system_message("🤔 Processing your request...")
        
        # Process the input in a worker thread
        self._current_worker = self.run_worker(
            self._process_agent_query(user_input),
            exclusive=True
        )
    
    async def _process_agent_query(self, query: str) -> str:
        """Process agent query in background.
        
        Args:
            query: User query to process
            
        Returns:
            Agent response
        """
        try:
            # Call the agent
            if hasattr(self.agent, 'query'):
                response = self.agent.query(query)
            else:
                response = str(self.agent(query))
            
            return response
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return f"Error: {str(e)}"
    
    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.worker == self._current_worker:
            chat_panel = self.query_one("#chat_panel", ChatPanel)
            
            if event.state == Worker.State.SUCCESS:
                # Get the result and display it
                result = event.worker.result
                chat_panel.add_message(result, sender="agent")
                
                # Save interaction to session
                self.call_after_refresh(self._save_interaction, event.worker.source, result)
                
                self._processing = False
                
            elif event.state == Worker.State.ERROR:
                # Handle error
                error_msg = str(event.worker.error) if event.worker.error else "Unknown error"
                chat_panel.add_error_message(f"Processing failed: {error_msg}")
                
                self._processing = False
                
            elif event.state == Worker.State.CANCELLED:
                chat_panel.add_warning_message("Processing cancelled")
                self._processing = False
    
    async def _save_interaction(self, query: str, response: str) -> None:
        """Save interaction to session."""
        try:
            # Get memory state if available
            memory_state = {}
            if hasattr(self.agent, 'get_session_state'):
                memory_state = self.agent.get_session_state()
            
            # Save to session
            await self.session_manager.save_interaction(query, response, memory_state)
            
        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")
    
    def on_multiline_input_cancelled(self, event: MultilineInput.Cancelled) -> None:
        """Handle input cancellation."""
        if self._processing and self._current_worker:
            self._current_worker.cancel()
            self._processing = False
            
            chat_panel = self.query_one("#chat_panel", ChatPanel)
            chat_panel.add_warning_message("❌ Processing cancelled")
    
    def action_quit(self) -> None:
        """Handle quit action."""
        if self._processing and self._current_worker:
            self._current_worker.cancel()
        
        self.app.exit()
    
    def action_refresh(self) -> None:
        """Refresh the screen."""
        self.refresh()
        
        chat_panel = self.query_one("#chat_panel", ChatPanel)
        chat_panel.add_system_message("🔄 Screen refreshed")
    
    async def action_save_session(self) -> None:
        """Save current session."""
        try:
            # Get memory state if available
            memory_state = {}
            if hasattr(self.agent, 'get_session_state'):
                memory_state = self.agent.get_session_state()
            
            # Save session
            await self.session_manager.save_session(memory_state)
            
            chat_panel = self.query_one("#chat_panel", ChatPanel)
            chat_panel.add_system_message("💾 Session saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            chat_panel = self.query_one("#chat_panel", ChatPanel)
            chat_panel.add_error_message(f"Failed to save session: {str(e)}")
    
    def action_export_chat(self) -> None:
        """Export chat conversation."""
        try:
            chat_panel = self.query_one("#chat_panel", ChatPanel)
            conversation = chat_panel.export_conversation(format="markdown")
            
            # Save to file
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.md', 
                delete=False,
                prefix=f'agentdk_chat_{self.agent_name}_'
            ) as f:
                f.write(conversation)
                temp_file = f.name
            
            chat_panel.add_system_message(f"📄 Chat exported to: {temp_file}")
            
        except Exception as e:
            logger.error(f"Failed to export chat: {e}")
            chat_panel = self.query_one("#chat_panel", ChatPanel)
            chat_panel.add_error_message(f"Failed to export chat: {str(e)}")
    
    def action_toggle_debug(self) -> None:
        """Toggle debug information."""
        # Future: Show debug information panel
        chat_panel = self.query_one("#chat_panel", ChatPanel)
        chat_panel.add_system_message("🔧 Debug mode not implemented yet")
    
    def cleanup(self) -> None:
        """Cleanup resources before exit."""
        try:
            # Cancel any running workers
            if self._current_worker:
                self._current_worker.cancel()
            
            # Save history
            self.history_manager.save()
            
            # Close session manager
            asyncio.create_task(self.session_manager.close())
            
            logger.info("ChatScreen cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")