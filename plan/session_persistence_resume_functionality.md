# Session Persistence and Resume Functionality Implementation Plan

**GitHub Issue:** [#7 - Memory: Add session persistence and resume functionality](https://github.com/breadpowder/agentdk/issues/7)

## 🎯 Issue Summary

Add persistent session management with resume capability to prevent memory loss between agent runs, with explicit session clearing options by default.

## 🔍 Current State Analysis

### Existing Implementation Strengths:
1. **Memory System Architecture** - Sophisticated 3-tier memory system:
   - `WorkingMemory`: Short-term session-aware context
   - `EpisodicMemory`: Long-term conversation history with compression  
   - `FactualMemory`: Persistent user preferences and structured knowledge
   - `MemoryManager`: Central coordinator with configurable LLM context pipeline

2. **CLI Infrastructure** - Basic session management exists:
   - `SessionManager` class in `src/agentdk/cli/session_manager.py`
   - JSON-based session storage in `~/.agentdk/sessions/`
   - `--resume` flag already implemented but not properly integrated
   - Stores conversation history per agent

3. **Memory-Aware Agents** - `MemoryAwareAgent` base class provides:
   - Memory initialization and management
   - Context-enhanced prompts
   - Conversation storage
   - User preference management

### Current Gaps:
1. **Integration Gap**: CLI SessionManager operates independently from AgentDK memory system
2. **Default Behavior**: Issue requests fresh memory by default, but current behavior is unclear
3. **Memory Integration**: `--resume` flag passes `memory=True` to agent but doesn't leverage CLI session state
4. **Session Commands**: Missing `agentdk sessions status` command

## 📋 Detailed Implementation Plan

### Phase 1: Core Integration (High Priority)

#### Task 1: Integrate CLI SessionManager with AgentDK Memory System
**Location**: `src/agentdk/cli/main.py`, `src/agentdk/cli/session_manager.py`

**Changes Needed**:
1. Modify `create_agent_instance()` to pass session context to memory-aware agents
2. Update `SessionManager` to work with `MemoryAwareAgent` memory state
3. Add session state conversion between CLI JSON format and memory system format

**Implementation**:
```python
# In main.py create_agent_instance()
if args.resume and hasattr(agent, 'memory') and agent.memory:
    session_manager = SessionManager(agent_name)
    session_loaded = await session_manager.load_session()
    if session_loaded:
        # Convert session context to memory format
        session_context = session_manager.get_session_context()
        agent.restore_from_session(session_context)

# In run_agent_interactive()
session_manager = SessionManager(agent_name) 
if not resume:
    await session_manager.start_new_session()
else:
    await session_manager.load_session()

# Save each interaction to both CLI session and agent memory
await session_manager.save_interaction(query, response)
```

#### Task 2: Modify CLI Default Behavior
**Location**: `src/agentdk/cli/main.py`

**Changes Needed**:
1. Change default behavior to start with fresh memory (clear previous state)
2. Make `--resume` explicit requirement to continue from previous session
3. Update help text and examples to reflect new behavior

**Implementation**:
```python
# Default behavior: fresh memory
agent_kwargs = {'memory': True}  # Memory enabled but fresh
if args.resume:
    agent_kwargs['resume_session'] = True  # Explicit resume flag

# In agent creation, handle session restoration differently
if not args.resume:
    # Clear any existing session for this agent
    session_manager = SessionManager(agent_name)
    session_manager.clear_session()
```

### Phase 2: Enhanced Session Management (Medium Priority)

#### Task 3: Add Session Status Commands
**Location**: `src/agentdk/cli/main.py`

**New CLI Commands**:
```bash
agentdk sessions status my_agent    # Show current session info
agentdk sessions list              # List all agent sessions  
agentdk sessions clear my_agent    # Clear specific agent session
agentdk sessions clear --all       # Clear all sessions
```

**Implementation**:
```python
# Add sessions subcommand parser
sessions_parser = subparsers.add_parser("sessions", help="Manage agent sessions")
sessions_subparsers = sessions_parser.add_subparsers(dest="sessions_command")

# Status command
status_parser = sessions_subparsers.add_parser("status", help="Show session status")
status_parser.add_argument("agent_name", help="Agent name to check")

# List command  
list_parser = sessions_subparsers.add_parser("list", help="List all sessions")

# Clear command
clear_parser = sessions_subparsers.add_parser("clear", help="Clear sessions")
clear_parser.add_argument("agent_name", nargs="?", help="Agent name to clear")
clear_parser.add_argument("--all", action="store_true", help="Clear all sessions")
```

#### Task 4: Enhanced Error Handling
**Location**: `src/agentdk/cli/session_manager.py`

**Error Scenarios to Handle**:
1. Corrupted session JSON files
2. Missing session directory permissions
3. Agent memory system initialization failures
4. Version compatibility issues with old session formats

**Implementation**:
```python
async def load_session(self) -> bool:
    """Enhanced session loading with robust error handling."""
    try:
        # Validate session file format and version
        if not self._validate_session_format():
            click.secho("Session file format outdated, starting fresh", fg="yellow")
            await self.start_new_session()
            return False
        
        # Load and validate session data
        session_data = self._load_and_validate_session()
        # ... existing logic with better error handling
        
    except (json.JSONDecodeError, KeyError) as e:
        click.secho(f"Session file corrupted: {e}, starting fresh", fg="yellow")
        await self._backup_corrupted_session()
        await self.start_new_session()
        return False
    except PermissionError as e:
        click.secho(f"Permission error accessing session: {e}", fg="red")
        raise
```

### Phase 3: Testing and Documentation (Medium-Low Priority)

#### Task 5: Comprehensive Testing
**Location**: `tests/cli/test_session_persistence.py` (new file)

**Test Scenarios**:
1. Fresh session start (default behavior)
2. Session resume with `--resume` flag
3. Session persistence across agent restarts
4. Memory integration between CLI and AgentDK memory system
5. Error handling for corrupted sessions
6. Session commands functionality

#### Task 6: Documentation Updates
**Location**: Update existing documentation

**Documentation Needed**:
1. Update CLI help text and examples
2. Add session management section to README/docs
3. Include examples of session workflow in CLAUDE.md

## 🔧 Technical Integration Details

### Memory System Integration Points

1. **MemoryAwareAgent.restore_from_session()** - New method to restore agent state from CLI session
2. **SessionManager.get_memory_state()** - Convert CLI session to memory system format
3. **SessionManager.save_memory_state()** - Store memory system state in CLI session

### Session Data Structure Enhancement

Current CLI session format:
```json
{
  "agent_name": "my_agent",
  "created_at": "2024-12-05T14:30:22Z",
  "interactions": [...]
}
```

Enhanced format with memory integration:
```json
{
  "agent_name": "my_agent", 
  "created_at": "2024-12-05T14:30:22Z",
  "last_updated": "2024-12-05T15:45:10Z",
  "format_version": "1.0",
  "interactions": [...],
  "memory_state": {
    "working_memory": [...],
    "user_preferences": {...},
    "session_metadata": {...}
  }
}
```

## ✅ Success Criteria Verification

1. **Fresh Memory Default**: `agentdk run my_agent` starts with clean memory ✓
2. **Explicit Resume**: `agentdk run my_agent --resume` continues from last session ✓  
3. **Automatic Session Management**: Sessions saved and managed automatically ✓
4. **Complete Context Preservation**: Resume maintains full conversation history ✓
5. **Error Handling**: Graceful handling of corrupted/missing sessions ✓
6. **CLI Feedback**: Clear status messages about session state ✓
7. **Documentation**: Updated examples and documentation ✓
8. **Testing**: Comprehensive test coverage ✓

## 🚀 Implementation Order

1. **Phase 1** - Core integration (high impact, enables key functionality)
2. **Phase 2** - Enhanced session management (improves user experience)  
3. **Phase 3** - Testing and documentation (ensures reliability and usability)

## 📝 Dependencies

- Existing `MemoryManager` and `MemoryAwareAgent` classes
- Current CLI infrastructure in `main.py` and `session_manager.py`
- Memory system configuration and initialization patterns

## 🎯 Expected Outcomes

- Improved development workflow with persistent debugging sessions
- Better user experience for long-running conversations  
- Ability to experiment with different conversation branches
- Enhanced testing capabilities with reproducible session states
- Clear, predictable session behavior that matches user expectations