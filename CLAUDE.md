# CLAUDE.md

This file provides guidance to Claude Code when working with the AgentDK repository.

## Dynamic Context Loading

Claude automatically loads relevant context from `.claude/` directory based on task type:

### Context Triggers
- **Agent Development** → `context`
- **Coding Rules**
    - **Exception Handling** → `rules/exception_handling.md`
    - **Testing** → `rules/testing_requirements.md`
- **Multi-step Tasks** → `rules/todo_management.md`
- **Architecture Questions** → `context`
- **Code Reviews** → `.claude/commands/code_review.md` (comprehensive workflow with GitHub integration)
- **GitHub Issues** → `.claude/commands/solve_github_issue.md`
- **Previous Planning** -> `plan/*`
- **Previous Github issues** -> `issue/*`

### Auto-Detection
- Working with `agent_interface.py` → Load agent development context
- Architecture/design questions → Load AgentDK architecture context
- User provided issue description, code review, or GitHub issues → Load comprehensive code review workflow
- Exception discussions → Load fail-fast principles

## Development and Testing Cond env Env
```bash
conda activate agentdk
```
**CRITICAL Environment Setup (Required for Integration Tests):**
```bash
# Install all dependencies including dev extras (langchain-openai for integration tests)
uv sync --extra dev

# Alternative: Install in development mode with dev dependencies
pip install -e .[dev]
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

### Logging Standards
- **Centralized Logging**: Use `get_logger()` from `agentdk.core.logging_config` for all logging
- **Logger Initialization**: Initialize loggers in class constructors: `self.logger = get_logger()`
- **Log Level Usage**:
  - `DEBUG`: Detailed tracing, internal state changes, debugging information
  - `INFO`: General operational messages, significant events
  - `WARNING`: Deprecated usage, recoverable errors, configuration issues
  - `ERROR`: Serious errors that don't stop execution
  - `CRITICAL`: Fatal errors that stop execution
- **Print Statement Migration**: Replace ALL print statements with appropriate logging calls
  - Status messages → `logger.debug()` or `logger.info()`
  - Error messages → `logger.warning()` or `logger.error()`
  - Debug output → `logger.debug()`
- **Message Format**: Centralized formatter provides: `timestamp - level - [module.function] - message`
- **Testing**: Use `caplog` fixture in tests to verify logging behavior when needed

**Example Implementation:**
```python
from ..core.logging_config import get_logger

class MyAgent:
    def __init__(self):
        self.logger = get_logger()
        self.logger.debug("Agent initialized")
    
    def process(self, data):
        self.logger.info(f"Processing {len(data)} items")
        try:
            # processing logic
            self.logger.debug("Processing completed successfully")
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
```

*Detailed patterns available in `.claude/patterns/`*

#
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
echo "how many customer" | uv run python -m agentdk.cli.main run examples/subagent/eda_agent.py

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

**CLI History Features:**
- **Global history file**: `~/.agentdk/cli_history.txt` shared across all agent sessions
- **Arrow key navigation**: ↑/↓ to navigate through last 10 commands
- **Non-blocking**: Preserves Ctrl+C signal handling for immediate response
- **Cross-agent sharing**: Commands available regardless of current agent
- **Auto-cleanup**: Maintains last 10 commands only, prevents file growth

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
- **Logging**: Centralized structured logging with module.function context (see Code Conventions → Logging Standards)

## Environment Configuration

### LLM Integration
- To run integration which requires llm loading, please use OPENAI_API_KEY from bash env