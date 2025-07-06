"""Agent loading and discovery for AgentDK CLI."""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional, Dict, Callable

import click

# Don't import get_llm at module level to avoid circular imports and dependency issues


class AgentLoader:
    """Loads agents from Python files and directories using various patterns."""
    
    def __init__(self):
        self._llm_providers: Dict[str, Callable] = {}
        self._setup_default_llm_providers()
    
    def _setup_default_llm_providers(self):
        """Setup default LLM provider factories."""
        # These can be extended based on available LLM providers
        self._llm_providers = {
            'openai': self._create_openai_llm,
            'anthropic': self._create_anthropic_llm,
        }
    
    def _create_openai_llm(self):
        """Create OpenAI LLM instance."""
        try:
            from openai import OpenAI
            return OpenAI()
        except ImportError:
            raise ImportError("OpenAI not installed. Run: pip install openai")
    
    def _create_anthropic_llm(self):
        """Create Anthropic LLM instance."""
        try:
            # This is a placeholder - adjust based on actual Anthropic client
            import anthropic
            return anthropic.Client()
        except ImportError:
            raise ImportError("Anthropic not installed. Run: pip install anthropic")
    
    def load_agent(self, agent_path: Path, llm_provider: Optional[str] = None, resume_session: bool = False) -> Any:
        """Load an agent from the given path.
        
        Args:
            agent_path: Path to Python file or directory containing agent
            llm_provider: Optional LLM provider name
            resume_session: Whether to resume from previous session
            
        Returns:
            Loaded and configured agent instance
            
        Raises:
            ValueError: If agent cannot be loaded
            ImportError: If required dependencies are missing
        """
        if agent_path.is_file():
            return self._load_agent_from_file(agent_path, llm_provider, resume_session)
        elif agent_path.is_dir():
            return self._load_agent_from_directory(agent_path, llm_provider, resume_session)
        else:
            raise ValueError(f"Invalid agent path: {agent_path}")
    
    def _load_agent_from_file(self, file_path: Path, llm_provider: Optional[str], resume_session: bool = False) -> Any:
        """Load agent from a Python file."""
        if not file_path.suffix == '.py':
            raise ValueError(f"Agent file must be a Python file (.py), got: {file_path}")
        
        # Strategy 1: Skip package loading for now to avoid recursion issues
        # Will implement better package support later
        parent_dir = file_path.parent
        
        # Strategy 2: Add the parent directory to sys.path to handle relative imports
        parent_dir_str = str(parent_dir)
        grandparent_dir_str = str(parent_dir.parent)
        
        # Add both parent and grandparent to handle different import patterns
        paths_added = []
        for path in [grandparent_dir_str, parent_dir_str]:  # Try grandparent first
            if path not in sys.path:
                sys.path.insert(0, path)
                paths_added.append(path)
        
        try:
            # Create a unique module name to avoid conflicts
            module_name = f"agentdk_cli_{file_path.stem}_{id(file_path)}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                raise ValueError(f"Cannot load module from {file_path}")
            
            module = importlib.util.module_from_spec(spec)
            # Don't add to sys.modules to avoid conflicts
            spec.loader.exec_module(module)
            
        except Exception as e:
            raise ValueError(f"Failed to load agent file {file_path}: {e}")
        finally:
            # Clean up sys.path
            for path in paths_added:
                if path in sys.path:
                    sys.path.remove(path)
        
        # Try different agent discovery patterns
        agent = self._discover_agent_in_module(module, llm_provider, resume_session)
        if agent is None:
            raise ValueError(f"No agent found in {file_path}. Expected factory function or agent instance.")
        
        return agent
    
    def _load_agent_from_directory(self, dir_path: Path, llm_provider: Optional[str], resume_session: bool = False) -> Any:
        """Load agent from a directory (package)."""
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            raise ValueError(f"Directory {dir_path} is not a Python package (missing __init__.py)")
        
        return self._load_agent_from_file(init_file, llm_provider, resume_session)
    
    def _discover_agent_in_module(self, module: Any, llm_provider: Optional[str], resume_session: bool = False) -> Optional[Any]:
        """Discover agent using various patterns."""
        
        # Pattern 1: Look for factory functions (create_*_agent)
        factory_functions = [
            name for name in dir(module) 
            if name.startswith('create_') and name.endswith('_agent') and callable(getattr(module, name))
        ]
        
        if factory_functions:
            # Use the first factory function found
            factory_func = getattr(module, factory_functions[0])
            
            # Get LLM instance or create mock
            if llm_provider:
                llm = self._get_llm_instance(llm_provider)
            else:
                # Try without LLM first, fallback to real LLM or mock if required
                try:
                    # CLI-loaded agents are user-facing (session management enabled)
                    return factory_func(resume_session=resume_session)
                except Exception as e:
                    if "LLM is required" in str(e) or "llm" in str(e).lower():
                        # Try to get a real LLM first
                        try:
                            from agentdk.utils.utils import get_llm
                            click.echo("No LLM specified, attempting to use available LLM...")
                            llm = get_llm()
                        except (ImportError, Exception) as llm_error:
                            click.echo(f"Real LLM not available ({llm_error}), using mock LLM for testing...")
                            llm = self._create_mock_llm()
                    else:
                        raise ValueError(f"Failed to create agent using {factory_functions[0]}: {e}")
            
            try:
                # CLI-loaded agents are user-facing (session management enabled)
                return factory_func(llm=llm, resume_session=resume_session)
            except Exception as e:
                raise ValueError(f"Failed to create agent using {factory_functions[0]}: {e}")
        
        # Pattern 2: Look for direct agent instance
        potential_agents = [
            name for name in dir(module)
            if not name.startswith('_') and hasattr(getattr(module, name), '__call__')
        ]
        
        for name in ['root_agent', 'agent'] + potential_agents:
            if hasattr(module, name):
                agent = getattr(module, name)
                # Basic validation that this looks like an agent
                if hasattr(agent, '__call__') or hasattr(agent, 'invoke'):
                    return agent
        
        return None
    
    def _get_llm_instance(self, llm_provider: str) -> Any:
        """Get LLM instance for the specified provider."""
        if llm_provider not in self._llm_providers:
            available = ', '.join(self._llm_providers.keys())
            raise ValueError(f"Unknown LLM provider: {llm_provider}. Available: {available}")
        
        return self._llm_providers[llm_provider]()
    
    def _create_mock_llm(self):
        """Create a mock LLM for testing when no real LLM is available."""
        class MockLLM:
            def invoke(self, input_data):
                if isinstance(input_data, dict):
                    input_text = input_data.get('input', str(input_data))
                else:
                    input_text = str(input_data)
                return {"output": f"Mock response to: {input_text}"}
            
            def __call__(self, input_text):
                return f"Mock response to: {input_text}"
            
            def bind(self, **kwargs):
                return self
        
        return MockLLM()