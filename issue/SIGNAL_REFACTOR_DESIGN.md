# Signal Handling Refactor Architecture Design

## Analysis Context & Background

### Initial Investigation Results
Based on comprehensive testing documented in `SIGNAL_TESTING_ANALYSIS.md`, the following critical issues were identified:

**Test Results Summary**:
- **research_agent.py** (no MCP): ✅ Clean shutdown, no errors
- **eda_agent.py** (with MCP): ❌ Async generator corruption during shutdown  
- **agent_app.py** (with MCP): ❌ Same async generator corruption pattern

**Error Pattern Observed**:
```
2025-07-13 16:32:32,707 - INFO - [main.cleanup_and_exit] - Shutdown complete
an error occurred during closing of asynchronous generator <async_generator object stdio_client>
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
RuntimeError: athrow(): asynchronous generator is already running
```

**Key Insight**: Errors occur during **normal shutdown** (not Ctrl+C interruption), consistently across all MCP-enabled agents.

### Initial Architecture Hypothesis (REJECTED)

**Initial Theory**: Task context mismatch between signal handlers and main execution
- Proposed complex signal coordination architecture
- Multiple new classes for signal queuing and processing
- Over-engineered solution for perceived "signal handling" problem

### Critical Re-Analysis: Evidence Re-Examination

**Crucial Detail**: Log sequence reveals actual root cause
```
2025-07-13 16:32:32,707 - INFO - [main.cleanup_and_exit] - Shutdown complete
an error occurred during closing of asynchronous generator...
```

**Critical Insight**: "Shutdown complete" appears BEFORE async generator errors

**Actual Root Cause Analysis**:
1. Main cleanup executes successfully
2. `sys.exit(0)` called prematurely  
3. Python garbage collection triggers async generator cleanup
4. Cleanup happens in wrong context (GC thread vs main thread)
5. Result: "different task" and "already running" errors

### Real Problem Identification

**The issue is NOT signal handling complexity** - it's **process exit timing and async resource lifecycle management**.

**Evidence Supporting This Conclusion**:
1. **Integration tests pass**: Subprocess execution doesn't trigger errors (different GC timing)
2. **Normal shutdown fails**: Timeout-triggered completion shows errors  
3. **MCP correlation**: Only MCP agents fail (only they have complex async generators)
4. **Timing dependency**: Error happens after "Shutdown complete" message

### Architectural Problems Identified

#### Problem 1: Premature Process Exit
**Location**: `main.py:cleanup_and_exit()`
```python
async def cleanup_and_exit(session_manager, history_manager):
    # ... cleanup logic ...
    logger.info("Shutdown complete")
    sys.exit(0)  # ❌ PROBLEM: Doesn't wait for async cleanup
```

**Issue**: `sys.exit(0)` terminates process while async generators are still active

#### Problem 2: Incomplete Async Resource Cleanup
**Location**: MCP session management lifecycle
```python
# Current: Async generators cleaned up by GC, not explicitly awaited
# Result: Cleanup happens in garbage collection context, not main task context
```

**Issue**: Async generators are garbage collected rather than properly awaited

#### Problem 3: Integration Test Coverage Gap
**Location**: `examples/integration_test/test_agent_sessions.py`
```python
# Current: Only validates stdout content, ignores stderr errors
user_response = extract_user_response(stdout)
# Missing: stderr error detection, exit code validation
```

**Issue**: Tests miss infrastructure failures that users experience

## Revised Minimal Architecture Design

### Design Principle: Minimal Intervention, Maximum Impact

**Core Concept**: Fix the actual root cause with minimal changes to working architecture, rather than over-engineering a complex signal handling system.

### Targeted Solution Components

#### Component 1: Proper Process Exit Coordination

**Current Problem**:
```python
async def cleanup_and_exit(session_manager, history_manager):
    # ... cleanup ...
    sys.exit(0)  # ❌ Exits before async cleanup complete
```

**Solution**: Natural function return with async coordination
```python
async def cleanup_and_exit(session_manager, history_manager):
    """Perform graceful cleanup and return naturally."""
    try:
        logger.info("Performing graceful shutdown...")
        
        # Session cleanup
        if session_manager:
            await session_manager.close()
            
        # History cleanup  
        if history_manager:
            history_manager.save()
            
        # MCP cleanup coordination
        await ensure_mcp_cleanup_complete()
        
        logger.info("Shutdown complete")
        # ✅ Return naturally, let main() exit cleanly
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        # Only exit with error code if cleanup fails
        sys.exit(1)
```

**Key Changes**:
- Remove premature `sys.exit(0)`
- Add MCP cleanup coordination
- Natural function return allows proper async cleanup
- Only exit with error code on actual failures

#### Component 2: Enhanced MCP Session Cleanup

**Current Problem**: No explicit coordination of MCP async generator cleanup

**Solution**: Explicit cleanup coordination with timeout protection
```python
async def ensure_mcp_cleanup_complete(timeout: float = 5.0):
    """Ensure all MCP sessions are properly cleaned up."""
    try:
        # Find all active MCP cleanup managers
        cleanup_tasks = []
        
        # Collect cleanup tasks from all active agents
        for manager in get_active_cleanup_managers():
            if hasattr(manager, 'cleanup') and callable(manager.cleanup):
                cleanup_tasks.append(manager.cleanup())
        
        if cleanup_tasks:
            # Wait for all cleanup with timeout protection
            await asyncio.wait_for(
                asyncio.gather(*cleanup_tasks, return_exceptions=True),
                timeout=timeout
            )
            logger.debug("MCP cleanup coordination complete")
            
    except asyncio.TimeoutError:
        logger.warning(f"MCP cleanup timed out after {timeout}s, forcing completion")
    except Exception as e:
        logger.error(f"MCP cleanup coordination failed: {e}")
```

**Key Features**:
- Explicit coordination of async generator cleanup
- Timeout protection prevents hanging
- Error isolation prevents cascade failures
- Runs in main task context (prevents "different task" errors)

#### Component 3: Robust Integration Test Enhancement

**Current Problem**: Tests ignore stderr errors and exit codes

**Solution**: Multi-modal validation with error detection
```python
def _run_agent_query_with_validation(agent_path: str, query: str, resume: bool = False) -> AgentTestResult:
    """Run agent query with comprehensive validation."""
    
    # ... existing subprocess execution ...
    
    stdout, stderr = process.communicate(input=query, timeout=60)
    
    # ✅ NEW: Comprehensive validation
    result = AgentTestResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=process.returncode,
        user_response=extract_user_response(stdout),
        has_signal_errors=detect_signal_errors(stderr),
        has_async_corruption=detect_async_corruption(stderr)
    )
    
    return result

def detect_signal_errors(stderr: str) -> bool:
    """Detect signal handling and async generator errors."""
    error_patterns = [
        "athrow(): asynchronous generator is already running",
        "Attempted to exit cancel scope in a different task",
        "RuntimeError.*cancel scope",
        "BaseExceptionGroup.*unhandled errors"
    ]
    return any(re.search(pattern, stderr) for pattern in error_patterns)

def test_agent_infrastructure_integrity():
    """Test that agents complete without infrastructure errors."""
    result = _run_agent_query_with_validation("examples/agent_app.py", "list tables")
    
    # Functional validation (existing)
    assert len(result.user_response.strip()) > 10
    
    # ✅ NEW: Infrastructure validation
    assert result.exit_code == 0, f"Agent exited with error code {result.exit_code}"
    assert not result.has_signal_errors, f"Signal handling errors detected: {result.stderr}"
    assert not result.has_async_corruption, f"Async corruption detected: {result.stderr}"
```

**Key Features**:
- Comprehensive error detection in stderr
- Exit code validation
- Pattern matching for known error types
- Preserves existing functional testing

#### Component 4: MCP Session Error Isolation

**Current Problem**: MCP session errors cascade and corrupt each other

**Solution**: Individual session error isolation
```python
async def cleanup_with_isolation(self):
    """Cleanup sessions with error isolation."""
    cleanup_results = await asyncio.gather(
        *[self._safe_cleanup_session(name, ctx) for name, ctx in self._session_contexts.items()],
        return_exceptions=True
    )
    
    # Log errors but don't let them cascade
    for i, (name, result) in enumerate(zip(self._session_contexts.keys(), cleanup_results)):
        if isinstance(result, Exception):
            logger.warning(f"Session {name} cleanup failed: {result}")
        else:
            logger.debug(f"Session {name} cleaned up successfully")

async def _safe_cleanup_session(self, name: str, session_ctx) -> None:
    """Cleanup individual session with timeout and error protection."""
    try:
        await asyncio.wait_for(session_ctx.exit(), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning(f"Session {name} cleanup timed out, forcing termination")
    except Exception as e:
        logger.warning(f"Session {name} cleanup error: {e}")
        # Don't re-raise - isolate the error
```

**Key Features**:
- Error isolation prevents cascade failures
- Individual session timeout protection
- Graceful degradation on cleanup failures

## Implementation Strategy

### Phase 1: Process Exit Fix (Immediate - High Impact)
**Target**: `src/agentdk/cli/main.py:cleanup_and_exit()`

**Changes**:
1. Remove `sys.exit(0)` from normal cleanup path
2. Add MCP cleanup coordination
3. Only exit with error code on actual failures
4. Let function return naturally for clean exit

**Expected Result**: Eliminates premature exit causing async generator GC issues

### Phase 2: MCP Cleanup Enhancement (High Priority)
**Target**: `src/agentdk/core/persistent_mcp.py`

**Changes**:
1. Add explicit cleanup coordination function
2. Implement timeout protection for cleanup operations
3. Add error isolation for individual sessions
4. Improve cleanup sequencing

**Expected Result**: Proper async resource cleanup, reduced corruption

### Phase 3: Integration Test Enhancement (Medium Priority)  
**Target**: `examples/integration_test/test_agent_sessions.py`

**Changes**:
1. Add stderr error detection
2. Add exit code validation
3. Add signal error pattern matching
4. Create infrastructure integrity tests

**Expected Result**: Tests detect the issues that users experience

### Phase 4: Validation and Monitoring (Ongoing)
**Target**: Comprehensive system validation

**Changes**:
1. Add integration tests for signal scenarios
2. Monitor for regression in signal handling
3. Validate cleanup timing improvements
4. Document proper shutdown procedures

**Expected Result**: Comprehensive coverage and early issue detection

## Success Criteria

### Immediate Success (Phase 1)
- [ ] No "Shutdown complete" followed by async generator errors
- [ ] Clean exit codes (0) for successful operations
- [ ] No premature process termination
- [ ] All existing functionality preserved

### Infrastructure Success (Phase 2) 
- [ ] MCP sessions cleanup without corruption
- [ ] Timeout protection prevents hanging
- [ ] Error isolation prevents cascade failures
- [ ] Graceful degradation on cleanup issues

### Testing Success (Phase 3)
- [ ] Integration tests detect signal handling failures
- [ ] stderr error monitoring catches infrastructure issues
- [ ] Exit code validation ensures clean termination
- [ ] Signal error patterns automatically detected

### System Success (Phase 4)
- [ ] Zero user reports of signal handling issues
- [ ] Improved CLI reliability and user experience
- [ ] Comprehensive test coverage for infrastructure
- [ ] Early detection of regression issues

## Risk Assessment

### Low Risk Changes
- **Process exit coordination**: Simple removal of premature exit
- **Integration test enhancement**: Additive validation, no behavior changes

### Medium Risk Changes  
- **MCP cleanup enhancement**: Touches critical session management code
- **Cleanup sequencing**: Could affect timing-sensitive operations

### Mitigation Strategies
- **Incremental rollout**: Implement and test each phase independently
- **Comprehensive testing**: Validate each change with existing test suite
- **Rollback procedures**: Keep changes isolated and easily reversible
- **Monitoring**: Add logging to detect any unintended side effects

## Alternative Approaches Considered

### Complex Signal Architecture (REJECTED)
**Approach**: Multiple new classes for signal coordination, event queuing, task context management
**Rejection Reason**: Over-engineering for a process exit timing issue

### MCP Library Replacement (REJECTED)
**Approach**: Replace langchain-mcp-adapters with custom implementation  
**Rejection Reason**: High risk, extensive changes, addresses symptom not cause

### Subprocess Integration Testing Only (REJECTED)
**Approach**: Accept that integration tests can't detect these issues
**Rejection Reason**: Leaves critical infrastructure gaps undetected

### Ignore Async Generator Errors (REJECTED)
**Approach**: Suppress errors as "harmless" since functionality works
**Rejection Reason**: Errors indicate real infrastructure problems that could worsen

## Conclusion

This minimal, targeted approach addresses the actual root cause (premature process exit and incomplete async cleanup) rather than over-engineering a complex signal handling solution. The solution:

1. **Targets the real problem**: Process exit timing, not signal handling complexity
2. **Minimizes risk**: Small, focused changes to critical paths
3. **Maximizes impact**: Eliminates user-visible async generator corruption  
4. **Improves testing**: Closes the gap between test coverage and user experience
5. **Maintains simplicity**: Preserves existing architecture while fixing critical issues

The evidence strongly supports that this targeted approach will resolve the signal handling issues without introducing unnecessary complexity or risk to the stable parts of the system.