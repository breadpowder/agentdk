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


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    logger.info("Received interrupt signal, shutting down...")
    sys.exit(0)


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
            from agentdk.utils.utils import llm
            kwargs['llm'] = llm
            logger.info("Using default LLM for agent")
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
    from .session_manager import SessionManager
    
    logger.info("Starting interactive mode (Ctrl+C to exit)")
    
    # Get agent name for session management
    agent_name = getattr(agent, '__class__').__name__.lower()
    if agent_name == 'type':
        agent_name = 'agent'  # fallback for unnamed agents
    
    # Initialize session manager
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
            logger.info("Starting with fresh memory")
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
        
        # Interactive loop
        while True:
            try:
                # Read from stdin or prompt
                if sys.stdin.isatty():
                    query = input(">>> ")
                else:
                    query = sys.stdin.read().strip()
                    if not query:
                        break
                
                if query.lower() in ['exit', 'quit', 'bye']:
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
        
        # Close session
        await session_manager.close()
                
    except Exception as e:
        logger.error(f"Interactive mode error: {e}")
        sys.exit(1)


async def handle_sessions_command(args):
    """Handle sessions subcommands."""
    from .session_manager import SessionManager
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
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
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
            agent_kwargs = {'memory': True}
            
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