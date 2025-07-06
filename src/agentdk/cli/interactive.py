"""Interactive REPL interface for AgentDK CLI."""

import asyncio
import signal
import sys
from typing import Any, Optional

import click

from ..agent.session_manager import SessionManager


class InteractiveCLI:
    """Interactive command-line interface for agent communication."""
    
    def __init__(self, agent: Any, agent_name: str, session_manager: SessionManager):
        self.agent = agent
        self.agent_name = agent_name
        self.session_manager = session_manager
        self._running = True
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown on Ctrl+C."""
        def signal_handler(signum, frame):
            click.echo("\n\nGracefully shutting down...")
            self._running = False
            # Exit immediately on Ctrl+C to avoid hanging on input()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Run the interactive REPL loop."""
        try:
            while self._running:
                try:
                    # Get user input
                    user_input = input(f"[user]: ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle special commands
                    if user_input.lower() in ['exit', 'quit', 'q']:
                        break
                    elif user_input.lower() == 'help':
                        self._show_help()
                        continue
                    elif user_input.lower() == 'clear':
                        click.clear()
                        continue
                    
                    # Process user query with agent
                    response = await self._process_query(user_input)
                    
                    # Display agent response
                    if response:
                        click.echo(f"[{self.agent_name}]: {response}")
                    
                    # Save interaction to session
                    await self.session_manager.save_interaction(user_input, response)
                    
                except EOFError:
                    # Handle Ctrl+D
                    break
                except KeyboardInterrupt:
                    # Handle Ctrl+C
                    break
                except Exception as e:
                    click.secho(f"Error processing query: {e}", fg="red")
        
        finally:
            await self._cleanup()
    
    async def _process_query(self, query: str) -> str:
        """Process user query with the agent."""
        try:
            # Use the high-level query() method which handles initialization and returns clean strings
            if hasattr(self.agent, 'query'):
                # AgentDK agent interface - returns clean string response
                result = await self._invoke_async(self.agent.query, query)
                return str(result)  # query() already returns a clean string
            elif hasattr(self.agent, '__call__'):
                # Direct callable interface fallback
                result = await self._invoke_async(self.agent, query)
                return str(result)
            else:
                return "Error: Agent does not have a recognized interface (query or __call__)"
                
        except Exception as e:
            return f"Error: {e}"
    
    async def _invoke_async(self, func, *args, **kwargs):
        """Invoke function asynchronously, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run sync function in executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)
    
    def _show_help(self):
        """Show help information."""
        help_text = f"""
Available commands:
  help    - Show this help message
  clear   - Clear the screen
  exit    - Exit the session (also: quit, q, Ctrl+D)
  
Agent: {self.agent_name}
Type your message and press Enter to chat with the agent.
"""
        click.echo(help_text)
    
    async def _cleanup(self):
        """Cleanup resources on shutdown."""
        click.echo(f"\nSession ended. Conversation saved for {self.agent_name}.")
        await self.session_manager.close()


async def run_interactive_session(agent: Any, agent_name: str, resume_session: bool = False):
    """Run an interactive session with the given agent.
    
    Args:
        agent: The agent instance to interact with
        agent_name: Name of the agent for display and session management
        resume_session: Whether to resume the previous session
    """
    # Initialize session manager for CLI agents
    session_manager = SessionManager(agent_name)
    
    if resume_session:
        await session_manager.load_session()
        click.echo("Previous session loaded.")
    else:
        await session_manager.start_new_session()
    
    # Create and run interactive CLI
    cli = InteractiveCLI(agent, agent_name, session_manager)
    await cli.run()