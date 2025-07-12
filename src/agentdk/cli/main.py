#!/usr/bin/env python3
"""AgentDK CLI - Command line interface for running agents."""

import argparse
import os
import sys
import signal
import asyncio
from pathlib import Path
from typing import Optional

from agentdk.core.logging_config import get_logger, set_log_level


logger = get_logger(__name__)

# Global shutdown event for coordinating signal handling with async code
shutdown_event = asyncio.Event()


class GlobalCLIHistory:
    """Manages global CLI command history across all agent sessions."""
    
    def __init__(self, max_size: int = 10):
        """Initialize global CLI history manager.
        
        Args:
            max_size: Maximum number of commands to keep in history
        """
        self.max_size = max_size
        self.history_file = Path.home() / ".agentdk" / "cli_history.txt"
        self.commands = self.load_and_cleanup()
        self.current_index = len(self.commands)
        logger.debug(f"Initialized global CLI history with {len(self.commands)} commands")
    
    def load_and_cleanup(self) -> list:
        """Load existing history and trim to max size.
        
        Returns:
            List of recent commands
        """
        if not self.history_file.exists():
            # Create directory if needed
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                all_commands = [line.strip() for line in f if line.strip()]
            
            # Keep only last max_size commands
            recent_commands = all_commands[-self.max_size:]
            
            # Immediately rewrite file with cleaned history
            self.save_commands(recent_commands)
            
            logger.debug(f"Loaded and cleaned history: {len(recent_commands)} commands")
            return recent_commands
            
        except (IOError, OSError) as e:
            logger.debug(f"Could not load history file: {e}")
            return []
    
    def add_command(self, command: str) -> None:
        """Add a command to history.
        
        Args:
            command: Command to add to history
        """
        if not command or not command.strip():
            return
        
        command = command.strip()
        
        # Avoid duplicate consecutive commands
        if self.commands and self.commands[-1] == command:
            return
        
        # Add command and maintain max size
        self.commands.append(command)
        if len(self.commands) > self.max_size:
            self.commands.pop(0)  # Remove oldest
        
        # Reset index to end of history
        self.current_index = len(self.commands)
        
        logger.debug(f"Added command to history: {command}")
    
    def get_previous(self) -> Optional[str]:
        """Get previous command in history.
        
        Returns:
            Previous command or None if at beginning
        """
        if not self.commands or self.current_index <= 0:
            return None
        
        self.current_index -= 1
        return self.commands[self.current_index]
    
    def get_next(self) -> Optional[str]:
        """Get next command in history.
        
        Returns:
            Next command or None if at end
        """
        if not self.commands or self.current_index >= len(self.commands) - 1:
            return None
        
        self.current_index += 1
        return self.commands[self.current_index]
    
    def save_commands(self, commands: list = None) -> None:
        """Save commands to history file.
        
        Args:
            commands: List of commands to save (defaults to current commands)
        """
        if commands is None:
            commands = self.commands
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                if commands:
                    f.write('\n'.join(commands) + '\n')
            
            logger.debug(f"Saved {len(commands)} commands to history file")
            
        except (IOError, OSError) as e:
            logger.debug(f"Could not save history file: {e}")
    
    def save(self) -> None:
        """Save current history to file."""
        self.save_commands()


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully by setting shutdown event."""
    logger.info("Received interrupt signal, initiating graceful shutdown...")
    # Use set_result on a future to signal from sync context to async context
    try:
        # Try to set the event if there's an active loop
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(shutdown_event.set)
    except RuntimeError:
        # No active loop, set the event directly
        shutdown_event.set()


def setup_dynamic_path(agent_file: Path):
    """Dynamically set up Python path for agent loading."""
    # Find the project root by looking for common project indicators
    current_dir = agent_file.parent.resolve()
    project_root = current_dir
    
    # Walk up the directory tree to find project root
    while project_root.parent != project_root:
        # Check for common project indicators
        indicators = ["pyproject.toml", "setup.py", "setup.cfg", ".git", "requirements.txt"]
        if any((project_root / indicator).exists() for indicator in indicators):
            break
        project_root = project_root.parent
    
    # Add all necessary paths to sys.path
    paths_to_add = [
        str(project_root),  # Project root for absolute imports
        str(current_dir),   # Agent file directory for local imports
    ]
    
    # Also add parent directories up to project root for nested imports
    temp_dir = current_dir
    while temp_dir != project_root and temp_dir.parent != temp_dir:
        temp_dir = temp_dir.parent
        paths_to_add.append(str(temp_dir))
    
    # Add paths if not already present
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    logger.debug(f"Added paths to sys.path: {paths_to_add}")
    return project_root


def load_agent_from_file(agent_file: Path):
    """Load an agent from a Python file with dynamic path resolution."""
    import importlib.util
    import inspect
    
    # Resolve the file path
    agent_file = agent_file.resolve()
    if not agent_file.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_file}")
    
    # Set up dynamic Python path
    project_root = setup_dynamic_path(agent_file)
    logger.info(f"Loading agent from: {agent_file}")
    logger.debug(f"Project root detected: {project_root}")
    
    try:
        # Load the module from file
        spec = importlib.util.spec_from_file_location("agent_module", agent_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec from {agent_file}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(module)
        
    except Exception as e:
        logger.error(f"Failed to load module: {e}")
        raise ImportError(f"Could not load agent module from {agent_file}: {e}") from e
    
    # Look for agent classes or factory functions
    agent_candidates = []
    
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            # Check if it's an agent class (has query method)
            if hasattr(obj, 'query') and not name.startswith('_'):
                agent_candidates.append((name, obj))
        elif inspect.isfunction(obj) and name.startswith('create_'):
            # Factory function
            agent_candidates.append((name, obj))
    
    if not agent_candidates:
        raise ValueError(f"No agent class or factory function found in {agent_file}")
    
    # Prefer classes over functions, and shorter names
    agent_candidates.sort(key=lambda x: (not inspect.isclass(x[1]), len(x[0])))
    
    name, agent_cls_or_func = agent_candidates[0]
    logger.info(f"Found agent: {name}")
    
    return agent_cls_or_func


def create_agent_instance(agent_cls_or_func, agent_file: Path, **kwargs):
    """Create an agent instance from class or factory function."""
    import inspect
    
    # Try to get a basic LLM if none provided
    if 'llm' not in kwargs:
        try:
            from agentdk.utils.utils import get_llm
            kwargs['llm'] = get_llm()
            logger.debug("Using default LLM for agent")
        except Exception as e:
            logger.warning(f"No LLM available: {e}")
            logger.warning("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
    
    if inspect.isclass(agent_cls_or_func):
        # Try to create instance
        try:
            return agent_cls_or_func(**kwargs)
        except TypeError as e:
            logger.error(f"Failed to create agent instance: {e}")
            logger.info("Try providing required arguments or use a factory function")
            raise
    else:
        # Factory function
        try:
            return agent_cls_or_func(**kwargs)
        except TypeError as e:
            logger.error(f"Failed to create agent with factory: {e}")
            raise



async def run_agent_interactive(agent, resume: bool = False):
    """Run agent in interactive mode with session management."""
    import sys
    from ..agent.session_manager import SessionManager
    
    # Clear any previous shutdown state
    shutdown_event.clear()
    
    logger.info("Starting interactive mode (Ctrl+C to exit)")
    
    # Get agent name for session management
    agent_name = getattr(agent, '__class__').__name__.lower()
    if agent_name == 'type':
        agent_name = 'agent'  # fallback for unnamed agents
    
    # Setup global CLI history
    history_manager = GlobalCLIHistory()
    
    # Initialize session manager for CLI-loaded agents
    session_manager = SessionManager(agent_name)
    
    try:
        if resume:
            logger.info("Resume mode enabled - loading previous session")
            session_loaded = await session_manager.load_session()
            
            # If agent supports memory restoration, restore from session
            if session_loaded and hasattr(agent, 'restore_from_session'):
                session_context = session_manager.get_session_context()
                if session_context:
                    success = agent.restore_from_session(session_context)
                    if success:
                        logger.info("Agent memory restored from session")
                    else:
                        logger.warning("Failed to restore agent memory from session")
        else:
            logger.debug("Starting with fresh memory")
            await session_manager.start_new_session()
            
            # Clear agent memory if supported
            if hasattr(agent, 'memory') and agent.memory:
                try:
                    # Clear working memory for fresh start
                    working_memory = getattr(agent.memory, 'working_memory', None)
                    if working_memory and hasattr(working_memory, 'clear'):
                        working_memory.clear()
                        logger.debug("Agent working memory cleared for fresh start")
                except Exception as e:
                    logger.warning(f"Could not clear agent memory: {e}")
        
        # Interactive loop with shutdown event coordination
        while not shutdown_event.is_set():
            try:
                # Get user input with history navigation support
                query = await get_user_input_with_history(history_manager)
                if query is None:  # Shutdown event was set or EOF
                    break
                
                if query.lower() in ['exit', 'quit', 'bye']:
                    break
                
                # Add command to history
                history_manager.add_command(query)
                
                # Check shutdown event before processing
                if shutdown_event.is_set():
                    break
                
                # Process query
                try:
                    response = agent.query(query) if hasattr(agent, 'query') else str(agent(query))
                    print(response)
                    
                    # Save interaction to session
                    memory_state = {}
                    if hasattr(agent, 'get_session_state'):
                        memory_state = agent.get_session_state()
                    
                    await session_manager.save_interaction(query, response, memory_state)
                    
                except Exception as e:
                    logger.error(f"Agent error: {e}")
                    print(f"Error: {e}")
                
                # If reading from pipe/file, exit after one query
                if not sys.stdin.isatty():
                    break
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\\nGoodbye!")
                break
        
        # Graceful cleanup
        await cleanup_and_exit(session_manager, history_manager)
                
    except Exception as e:
        logger.error(f"Interactive mode error: {e}")
        await cleanup_and_exit(session_manager, history_manager)
        sys.exit(1)


async def get_user_input_with_history(history_manager: GlobalCLIHistory):
    """Get user input with arrow key history navigation.
    
    Args:
        history_manager: Global CLI history manager
        
    Returns:
        User input string or None if shutdown requested
    """
    import sys
    import select
    import termios
    import tty
    
    try:
        if not sys.stdin.isatty():
            # Non-interactive mode (pipe/file input) - read all at once
            content = sys.stdin.read()
            return content.strip() if content else None
        
        # Interactive mode with arrow key support
        sys.stdout.write(">>> ")
        sys.stdout.flush()
        
        # Set up terminal for character-by-character input
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin)
        
        current_line = ""
        cursor_pos = 0
        temp_index = len(history_manager.commands)  # Start at end of history
        
        try:
            while not shutdown_event.is_set():
                # Check for input availability
                ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                if not ready:
                    await asyncio.sleep(0.01)
                    continue
                
                char = sys.stdin.read(1)
                
                if char == '\x03':  # Ctrl+C
                    return None
                elif char == '\x04':  # Ctrl+D (EOF)
                    return None
                elif char == '\r' or char == '\n':  # Enter
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    return current_line
                elif char == '\x7f' or char == '\x08':  # Backspace
                    if cursor_pos > 0:
                        current_line = current_line[:cursor_pos-1] + current_line[cursor_pos:]
                        cursor_pos -= 1
                        # Redraw line
                        sys.stdout.write('\r>>> ' + current_line + ' ')
                        sys.stdout.write('\r>>> ' + current_line)
                        if cursor_pos < len(current_line):
                            sys.stdout.write('\b' * (len(current_line) - cursor_pos))
                        sys.stdout.flush()
                elif char == '\x1b':  # Escape sequence (arrow keys)
                    # Read the next two characters for arrow key detection
                    next_chars = sys.stdin.read(2)
                    if next_chars == '[A':  # Up arrow
                        temp_index -= 1
                        if temp_index >= 0 and temp_index < len(history_manager.commands):
                            current_line = history_manager.commands[temp_index]
                            cursor_pos = len(current_line)
                            # Redraw line
                            sys.stdout.write('\r>>> ' + ' ' * 50)  # Clear line
                            sys.stdout.write('\r>>> ' + current_line)
                            sys.stdout.flush()
                        else:
                            temp_index = max(-1, temp_index)
                    elif next_chars == '[B':  # Down arrow
                        temp_index += 1
                        if temp_index < len(history_manager.commands):
                            current_line = history_manager.commands[temp_index]
                            cursor_pos = len(current_line)
                        else:
                            temp_index = len(history_manager.commands)
                            current_line = ""
                            cursor_pos = 0
                        # Redraw line
                        sys.stdout.write('\r>>> ' + ' ' * 50)  # Clear line
                        sys.stdout.write('\r>>> ' + current_line)
                        sys.stdout.flush()
                    elif next_chars == '[C':  # Right arrow
                        if cursor_pos < len(current_line):
                            cursor_pos += 1
                            sys.stdout.write('\x1b[C')
                            sys.stdout.flush()
                    elif next_chars == '[D':  # Left arrow
                        if cursor_pos > 0:
                            cursor_pos -= 1
                            sys.stdout.write('\x1b[D')
                            sys.stdout.flush()
                elif ord(char) >= 32:  # Printable character
                    current_line = current_line[:cursor_pos] + char + current_line[cursor_pos:]
                    cursor_pos += 1
                    # Redraw from cursor position
                    sys.stdout.write(char)
                    if cursor_pos < len(current_line):
                        remainder = current_line[cursor_pos:]
                        sys.stdout.write(remainder)
                        sys.stdout.write('\b' * len(remainder))
                    sys.stdout.flush()
                
                await asyncio.sleep(0.001)  # Small delay to prevent busy waiting
        
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        return None  # Shutdown event was set
        
    except (KeyboardInterrupt, EOFError):
        return None
    except ImportError:
        # termios not available (Windows), fall back to basic input
        return await get_user_input_basic()


async def get_user_input_basic():
    """Basic user input fallback for systems without termios."""
    import sys
    import select
    
    try:
        # Display prompt
        sys.stdout.write(">>> ")
        sys.stdout.flush()
        
        # Check if stdin is available for reading without blocking
        while not shutdown_event.is_set():
            if sys.stdin.isatty():
                # Interactive mode - use select to check for input availability
                ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                if ready:
                    # Input is available, read it
                    line = sys.stdin.readline()
                    if line:
                        return line.strip()
                    else:
                        # EOF encountered
                        return None
            else:
                # Non-interactive mode (pipe/file input) - read all at once
                content = sys.stdin.read()
                return content.strip() if content else None
            
            # Small delay to prevent busy waiting
            await asyncio.sleep(0.1)
        
        # Shutdown event was set
        return None
        
    except (KeyboardInterrupt, EOFError):
        return None


async def cleanup_and_exit(session_manager, history_manager: GlobalCLIHistory = None):
    """Perform graceful cleanup before exit."""
    try:
        logger.info("Performing graceful shutdown...")
        print("\nGracefully shutting down...")
        
        # Save global CLI history
        if history_manager:
            history_manager.save()
        
        # Save session state
        await session_manager.close()
        logger.info("Session state saved successfully")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    logger.info("Shutdown complete")
    # Actually exit the process
    sys.exit(0)


async def handle_sessions_command(args):
    """Handle sessions subcommands."""
    from ..agent.session_manager import SessionManager
    import click
    
    if args.sessions_command == "status":
        # Show status for specific agent
        session_manager = SessionManager(args.agent_name)
        session_info = session_manager.get_session_info()
        
        if not session_info.get("exists", False):
            click.echo(f"No session found for agent: {args.agent_name}")
            return
        
        if session_info.get("corrupted", False):
            click.secho(f"Session corrupted for {args.agent_name}: {session_info.get('error', 'Unknown error')}", fg="red")
            return
        
        click.echo(f"Session Status for {args.agent_name}:")
        click.echo(f"  Created: {session_info.get('created_at', 'unknown')}")
        click.echo(f"  Last Updated: {session_info.get('last_updated', 'unknown')}")
        click.echo(f"  Format Version: {session_info.get('format_version', 'unknown')}")
        click.echo(f"  Interactions: {session_info.get('interaction_count', 0)}")
        click.echo(f"  Has Memory State: {session_info.get('has_memory_state', False)}")
        
    elif args.sessions_command == "list":
        # List all sessions
        session_dir = Path.home() / ".agentdk" / "sessions"
        if not session_dir.exists():
            click.echo("No sessions directory found")
            return
        
        session_files = list(session_dir.glob("*_session.json"))
        if not session_files:
            click.echo("No sessions found")
            return
        
        click.echo("Available Sessions:")
        for session_file in session_files:
            agent_name = session_file.stem.replace("_session", "")
            session_manager = SessionManager(agent_name)
            session_info = session_manager.get_session_info()
            
            status = "✓" if not session_info.get("corrupted", False) else "✗"
            interaction_count = session_info.get("interaction_count", 0)
            last_updated = session_info.get("last_updated", "unknown")
            
            click.echo(f"  {status} {agent_name} - {interaction_count} interactions (last: {last_updated})")
    
    elif args.sessions_command == "clear":
        # Clear sessions
        if args.all:
            # Clear all sessions
            session_dir = Path.home() / ".agentdk" / "sessions"
            if session_dir.exists():
                session_files = list(session_dir.glob("*_session.json"))
                for session_file in session_files:
                    try:
                        session_file.unlink()
                        click.echo(f"Cleared session: {session_file.stem.replace('_session', '')}")
                    except Exception as e:
                        click.secho(f"Failed to clear {session_file.name}: {e}", fg="red")
                click.echo(f"Cleared {len(session_files)} sessions")
            else:
                click.echo("No sessions directory found")
        elif args.agent_name:
            # Clear specific agent session
            session_manager = SessionManager(args.agent_name)
            if session_manager.has_previous_session():
                session_manager.clear_session()
                click.echo(f"Cleared session for {args.agent_name}")
            else:
                click.echo(f"No session found for {args.agent_name}")
        else:
            click.echo("Specify agent name or use --all to clear all sessions")
    
    else:
        click.echo("Invalid sessions command")


def main():
    """Main CLI entry point."""
    # Note: Signal handlers are managed by the MCP system in persistent_mcp.py
    # We coordinate with shutdown_event which gets set by the MCP signal handler
    
    parser = argparse.ArgumentParser(
        description="AgentDK CLI - Run intelligent agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agentdk run agent.py                    # Run agent with fresh memory (default)
  agentdk run agent.py --resume           # Resume from previous session
  agentdk run examples/eda_agent.py       # Run example agent
  echo "query" | agentdk run agent.py     # Pipe input to agent
  agentdk sessions status my_agent        # Show session status
  agentdk sessions list                   # List all sessions
  agentdk sessions clear my_agent         # Clear specific session
  agentdk sessions clear --all            # Clear all sessions
        """
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run an agent")
    run_parser.add_argument(
        "agent_file",
        type=Path,
        help="Path to Python file containing agent"
    )
    run_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous session (default: start with fresh memory)"
    )
    
    # Sessions command
    sessions_parser = subparsers.add_parser("sessions", help="Manage agent sessions")
    sessions_subparsers = sessions_parser.add_subparsers(dest="sessions_command", help="Session commands")
    
    # Status command
    status_parser = sessions_subparsers.add_parser("status", help="Show session status")
    status_parser.add_argument("agent_name", help="Agent name to check")
    
    # List command  
    list_parser = sessions_subparsers.add_parser("list", help="List all sessions")
    
    # Clear command
    clear_parser = sessions_subparsers.add_parser("clear", help="Clear sessions")
    clear_parser.add_argument("agent_name", nargs="?", help="Agent name to clear")
    clear_parser.add_argument("--all", action="store_true", help="Clear all sessions")
    
    args = parser.parse_args()
    
    # Set up logging
    set_log_level(args.log_level)
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "run":
        if not args.agent_file.exists():
            logger.error(f"Agent file not found: {args.agent_file}")
            sys.exit(1)
        
        try:
            # Load agent
            agent_cls_or_func = load_agent_from_file(args.agent_file)
            
            # Create instance with memory enabled by default
            # CLI-loaded agents are user-facing (session management enabled)
            agent_kwargs = {
                'memory': True,
                'resume_session': args.resume
            }
            
            agent = create_agent_instance(agent_cls_or_func, args.agent_file, **agent_kwargs)
            
            # Run interactively
            asyncio.run(run_agent_interactive(agent, resume=args.resume))
            
        except Exception as e:
            logger.error(f"Failed to run agent: {e}")
            sys.exit(1)
    
    elif args.command == "sessions":
        asyncio.run(handle_sessions_command(args))


if __name__ == "__main__":
    main()