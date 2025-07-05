"""AgentDK CLI main entry point with Click framework."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from .agent_loader import AgentLoader
from .interactive import run_interactive_session


@click.group(context_settings={"max_content_width": 240})
@click.version_option(version="0.1.0")
def main():
    """AgentDK CLI tools for interactive agent deployment."""
    pass


@main.command("run")
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="Resume the last session for this agent.",
)
@click.option(
    "--llm",
    type=str,
    help="LLM provider to use (e.g., 'openai', 'anthropic'). Uses agent default if not specified.",
)
@click.argument(
    "agent_path",
    type=click.Path(exists=True, resolve_path=True),
    required=True,
)
def cli_run(agent_path: str, resume: bool, llm: Optional[str]):
    """Run an interactive CLI session for an agent.
    
    AGENT_PATH: Path to Python file or directory containing agent factory function.
    
    Examples:
        agentdk run examples/subagent/eda_agent.py
        agentdk run examples/subagent/research_agent.py --resume
        agentdk run examples/my_agent/ --llm anthropic
    """
    try:
        # Load the agent
        agent_path_obj = Path(agent_path)
        loader = AgentLoader()
        
        click.echo(f"Loading agent from {agent_path}...")
        agent = loader.load_agent(agent_path_obj, llm_provider=llm)
        
        # Get agent name for session management
        agent_name = getattr(agent, 'name', None) or agent_path_obj.stem
        
        click.echo(f"Agent '{agent_name}' ready. Type 'exit' to quit, 'help' for commands.")
        
        # Run interactive session
        asyncio.run(run_interactive_session(
            agent=agent,
            agent_name=agent_name,
            resume_session=resume
        ))
        
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()