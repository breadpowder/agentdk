# CLAUDE.md

This file provides guidance to Claude Code when working with the AgentDK repository.

## Dynamic Context Loading

Claude automatically loads relevant context from `.claude/` directory based on task type:

### Context Triggers
- **Agent Development** → `.claude/contexts/python_agent_dev.md`
- **Architecture Questions** → `.claude/contexts/agentdk_architecture.md`
- **Code Reviews** → `.claude/commands/code_review.md` (comprehensive workflow with GitHub integration)
- **GitHub Issues** → `.claude/commands/solve_github_issue.md`
- **Exception Handling** → `.claude/patterns/exception_handling.md`
- **Testing Issues** → `.claude/patterns/testing_requirements.md`
- **Multi-step Tasks** → `.claude/patterns/todo_management.md`
- **Previous Planning** -> `plan/`

### Auto-Detection
- Working with `agent_interface.py` → Load agent development context
- Architecture/design questions → Load AgentDK architecture context
- User provided issue description, code review, or GitHub issues → Load comprehensive code review workflow
- Exception discussions → Load fail-fast principles
- MCP/async issues → Load session management lessons
- GitHub issue numbers → Load GitHub issue workflow integration

## Development Commands
switch to agentdk env

```bash
conda activate agentdk
```
Sometimes, you need to run to update env
```bash
pip install -e .[dev]
```

### Testing & Quality
```bash
# Run tests (unit tests only by default, excludes integration)
python -m pytest tests/ -v

# Run specific test modules
python -m pytest tests/builder/ -v        # Builder pattern tests
python -m pytest tests/core/ -v           # Core functionality tests  
python -m pytest tests/memory/ -v         # Memory system tests
python -m pytest tests/utils/ -v          # Utility function tests
python -m pytest tests/agent/ -v          # Agent interface tests

# Run integration tests (requires OPENAI_API_KEY)
python -m pytest examples/integration_test/ -v -m integration

# Run all tests including integration
python -m pytest tests/ examples/integration_test/ -v

# Run specific integration test scenarios
python -m pytest examples/integration_test/test_agent_sessions.py::test_fresh_agent_session -v

# Format code
black src/ tests/ examples/
isort src/ tests/ examples/

# Type checking
mypy src/agentdk

# Package management
uv sync                    # Install dependencies
uv add <package>           # Add dependency
uv remove <package>        # Remove dependency
```

## Test Structure

Tests are organized to mirror the source structure:

```
tests/                     # Mirrors src/agentdk/
├── agent/                 # → src/agentdk/agent/
│   ├── __init__.py
│   └── test_factory.py
├── builder/               # → src/agentdk/builder/
│   ├── __init__.py
│   └── test_agent_builder.py
├── core/                  # → src/agentdk/core/
│   ├── __init__.py
│   ├── test_logging_config.py
│   ├── test_mcp_load.py
│   └── test_persistent_mcp.py
├── memory/                # → src/agentdk/memory/
│   ├── __init__.py
│   └── test_memory_aware_agent.py
├── utils/                 # → src/agentdk/utils/
│   ├── __init__.py
│   └── test_utils.py
├── conftest.py           # Global test configuration
├── test_exceptions.py    # Top-level exception tests
└── test_init.py         # Package initialization tests
```

## Integration Tests

Integration tests are located in `examples/integration_test/` and require external dependencies (API keys). They are excluded from default test runs to improve developer experience.

### Test Categories

**Unit Tests** (`@pytest.mark.unit`):
- Fast, isolated tests without external dependencies
- Run by default with `python -m pytest tests/ -v`
- Should not require API keys or external services

**Integration Tests** (`@pytest.mark.integration`):
- End-to-end tests requiring API keys and external services
- Test agent session management, memory persistence, CLI workflows
- Require `OPENAI_API_KEY` environment variable
- Run explicitly with `python -m pytest examples/integration_test/ -v -m integration`

### Integration Test Scenarios

**Test Coverage**:
1. **Fresh Session Start**: Verify agent starts with clean memory
2. **Session Resumption**: Test `--resume` flag and memory persistence
3. **Memory Learning**: Validate memory context and user correction handling
4. **Sub-agent Functionality**: Test EDA agent workflows

**Environment Requirements**:
```bash
# Required for integration tests
export OPENAI_API_KEY="your-api-key"

# Optional for extended testing
export ANTHROPIC_API_KEY="your-anthropic-key"
```

**Test Execution Examples**:
```bash
# Default: Unit tests only (fast, no API keys needed)
python -m pytest tests/ -v

# Integration tests only (requires OPENAI_API_KEY)
python -m pytest examples/integration_test/ -v -m integration

# All tests including integration
python -m pytest tests/ examples/integration_test/ -v

# Specific integration test
python -m pytest examples/integration_test/test_agent_sessions.py::test_fresh_agent_session -v
```


## Code Conventions

### Python Standards
- **Type Annotations**: ALWAYS add typing annotations with return types
- **Docstrings**: Use PEP257 convention
- **Testing**: Use pytest exclusively (NOT unittest module)
- **Imports**: Use isort for consistent organization

### Core Principles
- **Inheritance Over Implementation**: Design inheritance patterns first, complete logic in parent class
- **Centralized Prompt Management**: Externalize prompts to `prompts.py` files
- **Abstraction Integrity**: Interact through provider's high-level public API only

*Detailed patterns available in `.claude/patterns/`*

## Quick Start

### Agent Creation
```python
from agentdk import create_agent, AgentConfig

# Using factory
config = AgentConfig(mcp_config_path='config.json')
agent = create_agent('eda', config=config, llm=llm)

# Memory-aware agent
from agentdk.memory import MemoryAwareAgent
class MyAgent(MemoryAwareAgent):
    def __call__(self, query):
        enhanced_input = self.process_with_memory(query)
        result = self.workflow.invoke(enhanced_input)
        return self.finalize_with_memory(query, result)

# Session-aware agent (NEW in v0.2.0)
class SessionAwareAgent(MemoryAwareAgent):
    def query(self, user_prompt: str, **kwargs) -> str:
        # Memory context automatically restored from CLI sessions
        memory_context = self.get_memory_context(user_prompt)
        enhanced_prompt = f"Context: {memory_context}\nQuery: {user_prompt}"
        result = super().query(enhanced_prompt, **kwargs)
        # Session state automatically saved by CLI
        return result
```

### MCP Session Management
```python
agent = EDAAgent(llm=llm)  # Persistent session created
agent.query("query1")      # Reuse session
agent.query("query2")      # Reuse session
# Sessions cleaned up automatically
```

*Full implementation patterns in `.claude/contexts/python_agent_dev.md`*

## Agent Interface Usage Patterns

### Method Selection Guidelines
When working with AgentDK agents, use the correct interface method:

**Use `agent.query()` method (line 176 in agent_interface.py) for:**
- CLI integration and interactive sessions
- Direct user queries requiring clean string responses
- Memory-aware conversations with session continuity
- Simple Q&A interactions

```python
# Correct for CLI and interactive use
result = agent.query("Show me the customer data")
# Returns: Clean string with formatted results
```

**Use `agent.invoke()` method for:**
- LangGraph state management and workflows
- Multi-agent supervisor integration
- Complex state transitions with message passing

```python
# Correct for LangGraph workflows
state = {"messages": [{"role": "user", "content": "query"}]}
result = agent.invoke(state)
# Returns: {"messages": [AIMessage(content="response")]}
```

### Memory Integration Patterns
When implementing memory-aware agents:

```python
# Memory-enhanced query processing
class MyAgent(MemoryAwareAgent):
    def __call__(self, query):
        # Process with memory context
        enhanced_input = self.process_with_memory(query)
        result = self.workflow.invoke(enhanced_input)
        return self.finalize_with_memory(query, result)
        
    def query(self, user_prompt: str, **kwargs) -> str:
        # Use memory-aware query for CLI compatibility
        memory_context = self.get_memory_context(user_prompt)
        enhanced_prompt = f"User query: {user_prompt}\nMemory context: {memory_context}"
        return super().query(enhanced_prompt, **kwargs)
```

## Task Workflow

### Standard Process
1. **Context Loading**: Check `.claude/` directory for relevant patterns
2. **Planning**: Use TodoWrite for complex tasks (3+ steps)
3. **Implementation**: Complete tasks one at a time, mark progress
4. **Testing**: MUST run tests after ANY code changes
5. **Quality**: Run lint/typecheck, verify fixes applied

### Interactive Development Workflow
For CLI development and iterative testing:

**Live Testing Patterns:**
```bash
# Test agent functionality with piped input
echo "query text" | uv run python -m agentdk.cli.main run examples/subagent/eda_agent.py

# Test session persistence (NEW in v0.2.0)
agentdk run agent.py --resume

# Test multi-agent systems
echo "complex query" | uv run python -m agentdk.cli.main run examples/agent_app.py
```

**Session Management (NEW in v0.2.0):**
```bash
# Default: Start with fresh memory
agentdk run my_agent.py

# Explicit: Resume from previous session  
agentdk run my_agent.py --resume

# Session management commands
agentdk sessions status my_agent        # Show session info
agentdk sessions list                   # List all sessions
agentdk sessions clear my_agent         # Clear specific session
agentdk sessions clear --all            # Clear all sessions
```

**Memory Integration Testing:**
1. **Session Continuity**: Test `--resume` flag to verify memory persistence
2. **Memory Context**: Validate memory-enhanced prompts include previous interactions
3. **Cross-Session State**: Ensure user preferences and context carry over
4. **Fresh Start**: Verify default behavior starts with clean memory
5. **Session Recovery**: Test corrupted session handling and backup creation

**Iterative Debugging Approach:**
1. Start with simple CLI test: `echo "test" | agentdk run agent.py`
2. Check agent initialization logs for MCP connectivity
3. Verify `agent.query()` method usage for clean responses
4. Test signal handling with Ctrl+C termination
5. Validate session management and memory integration

### Testing Rule
**CRITICAL**: You MUST run `python -m pytest tests/ -v` after code modifications. Tests must pass before task completion.

**Test Organization Guidelines**:
- Place tests in directories that mirror `src/agentdk/` structure
- New modules in `src/agentdk/foo/` should have tests in `tests/foo/`
- Include `__init__.py` files in all test directories
- Use descriptive test file names: `test_<module_name>.py`

### Commit Guidelines
NEVER commit unless explicitly requested. When committing:
- Descriptive messages covering all changes
- Include performance improvements
- Add co-authorship attribution

*Detailed workflows in `.claude/commands/code_review.md` (comprehensive GitHub-integrated workflow), patterns in `.claude/patterns/`, architecture in `.claude/contexts/agentdk_architecture.md`*

## Important Notes
- **Jupyter Compatibility**: Framework includes nest_asyncio for IPython
- **Path Resolution**: Relative paths resolved relative to config file location
- **Error Handling**: Graceful degradation with detailed error messages
- **Logging**: Centralized JSON-formatted logging

## Environment Configuration

### LLM Integration
- To run integration which requires llm loading, please use OPENAI_API_KEY from bash env