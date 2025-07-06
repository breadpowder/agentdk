# [Enhancement] Memory: Add session persistence and resume functionality

## Summary
- **One-sentence description**: Add persistent session management with automatic resume capability and explicit session clearing options to prevent memory loss between agent runs
- **Impact level**: High
- **Component affected**: Memory/Core/CLI

## Current Behavior
- **What exists today**: AgentDK currently starts each agent execution with a fresh memory state, losing all previous conversation history and context
- **Pain points**: 
  - Users lose valuable conversation context when restarting agents
  - No way to continue from where a previous session left off
  - Debugging and development workflows are interrupted by memory resets
  - Long conversations cannot be resumed after interruptions
- **Limitations**: 
  - No persistent storage of agent sessions
  - No mechanism to resume from previous interactions
  - Memory is completely reset on each agent execution

## Desired Behavior
- **Improved functionality**: 
  - `run` command should support `--resume` flag to continue from last session
  - `run` command should support `--fresh` flag to explicitly start with empty memory
  - By default, `run` command should resume from the most recent session if available
  - Sessions should be automatically saved and managed by the memory system
  - `resume` command should be available as a standalone command for convenience
- **Benefits**: 
  - Improved development workflow with persistent debugging sessions
  - Better user experience for long-running conversations
  - Ability to experiment with different conversation branches
  - Enhanced testing capabilities with reproducible session states
- **Success metrics**: 
  - Sessions persist correctly across restarts
  - Resume functionality maintains complete conversation context
  - Performance impact is minimal for session loading/saving
  - User workflow interruptions are eliminated

## Integration Analysis
- **Current approach**: Memory is handled in-memory only with no persistence layer
- **Alternative approaches**:
  1. **File-based sessions**: Save sessions as JSON files (similar to Google ADK approach)
     - Pros: Simple implementation, human-readable, easy debugging
     - Cons: Limited scalability, potential file system issues
  2. **Database-backed sessions**: Use SQLite or other database for session storage
     - Pros: Better performance, transaction support, querying capabilities
     - Cons: Additional complexity, dependency management
  3. **Hybrid approach**: File-based for development, database for production
     - Pros: Best of both worlds, flexible deployment
     - Cons: Increased complexity, multiple code paths
- **Technology comparison**: File-based approach recommended for initial implementation due to simplicity and Google ADK compatibility

## Acceptance Criteria
- [ ] `run my_agent` automatically resumes from last session if available
- [ ] `run my_agent --fresh` starts with completely empty memory
- [ ] `run my_agent --resume` explicitly continues from last session
- [ ] `resume my_agent` standalone command works as shortcut for `run my_agent --resume`
- [ ] Sessions are automatically saved and managed by the memory system
- [ ] Session loading preserves complete conversation history and memory state
- [ ] Error handling for corrupted or missing session data
- [ ] CLI provides clear feedback about session status (new/resumed/not found)
- [ ] Documentation updated with session management examples
- [ ] Tests passing for all session persistence scenarios

## Proposed CLI Interface

```bash
# Default behavior - resume from last session if available
agentdk run my_agent

# Explicitly start fresh session
agentdk run my_agent --fresh

# Resume from last session (explicit)
agentdk run my_agent --resume

# Standalone resume command
agentdk resume my_agent

# View current session status
agentdk sessions status my_agent

# Clean old sessions
agentdk sessions clean --older-than 7d
```

## Session Data Structure
```json
{
  "agent_name": "my_agent",
  "created_at": "2024-12-05T14:30:22Z",
  "last_updated": "2024-12-05T15:45:10Z",
  "conversation_history": [...],
  "memory_state": {...},
  "agent_config": {...}
}
```

## Related Work
This enhancement draws inspiration from Google ADK's session management approach, which provides similar functionality with `--save_session`, `--resume`, and `--replay` options. The proposed implementation should be compatible with this pattern while providing a more user-friendly default behavior.