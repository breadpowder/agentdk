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



def run_agent_interactive(agent, resume: bool = False):
    """Run agent in interactive mode."""
    import sys
    
    logger.info("Starting interactive mode (Ctrl+C to exit)")
    
    if resume:
        logger.info("Resume mode enabled - previous conversations will be remembered")
    
    try:
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
                
    except Exception as e:
        logger.error(f"Interactive mode error: {e}")
        sys.exit(1)


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
  agentdk run agent.py                    # Run agent interactively
  agentdk run examples/eda_agent.py       # Run example agent
  echo "query" | agentdk run agent.py     # Pipe input to agent
  agentdk run agent.py --resume           # Resume previous session
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
        help="Resume previous conversation (if agent supports memory)"
    )
    
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
            
            # Create instance
            agent_kwargs = {}
            if args.resume:
                agent_kwargs['memory'] = True
            
            agent = create_agent_instance(agent_cls_or_func, args.agent_file, **agent_kwargs)
            
            # Run interactively
            run_agent_interactive(agent, resume=args.resume)
            
        except Exception as e:
            logger.error(f"Failed to run agent: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()