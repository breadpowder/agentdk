# [Feature] CLI: Add command-line interface support for interactive agent deployment

## Summary
- **One-sentence description**: Add CLI support to AgentDK enabling users to start agents as interactive command-line applications by specifying their main agent Python file
- **Impact level**: Medium
- **Component affected**: Core/Agent Interface

## Problem Statement
- **Current limitations**: AgentDK agents can only be deployed programmatically through Python scripts, requiring users to write custom scripts for interaction
- **Use cases**: 
  - Developers need quick interactive testing of agents during development
  - Users want to deploy agents as CLI applications without writing wrapper scripts
  - Teams need consistent deployment patterns across different agent types
- **Business value**: Reduces barrier to entry, improves developer experience, and provides professional deployment option

## Proposed Solution
- **High-level approach**: Add a CLI module that dynamically loads agent Python files and provides interactive REPL interface
- **User experience**: Simple command `agentdk start --<agent_file>` launches interactive session
- **Integration points**: Integrates with existing agent factory, configuration system, and all agent types (EDA, Research, custom)

## Technical Requirements
- **Core functionality**: 
  - Python file parser to detect agent instances/classes
  - Interactive REPL with command history
  - Session management and graceful shutdown
  - Cross-platform compatibility
- **Implementation scope**: Core CLI module in `src/agentdk/cli/`
- **Dependencies**: Click or Typer for CLI framework, Rich for terminal output (optional)
- **Performance considerations**: Fast startup time, minimal memory overhead
- **Security considerations**: Validate Python files before execution, sandbox execution environment

## Acceptance Criteria
- [ ] CLI can start any agent from a Python file using `agentdk start --<file>`
- [ ] Interactive mode supports multi-turn conversations with full agent functionality
- [ ] Graceful error handling for invalid files, missing agents, or configuration issues
- [ ] Proper signal handling (Ctrl+C for graceful shutdown)
- [ ] Command history and basic auto-completion
- [ ] Documentation with examples for different agent types
- [ ] Unit tests covering CLI functionality with >80% coverage
- [ ] Integration tests with existing example agents

**Note**: Do not include implementation details, code samples, or specific API designs in GitHub issues. These should be planned during the implementation phase.
