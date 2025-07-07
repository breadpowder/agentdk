# GitHub Issue #12: Integration Test Tags Implementation Plan

**GitHub Issue:** [#12 - Testing: Add integration test tags for end-to-end agent scenarios](https://github.com/breadpowder/agentdk/issues/12)

## 🎯 Issue Summary

Add pytest markers for integration tests that require API keys and external dependencies, with selective execution capabilities to improve developer experience and CI/CD pipelines.

## 📊 Current State Analysis

### Existing Infrastructure ✅
- **Pytest markers already configured** in both `pytest.ini` and `pyproject.toml`:
  ```ini
  markers =
      slow: marks tests as slow (deselect with '-m "not slow"')
      integration: marks tests as integration tests
      unit: marks tests as unit tests
  ```
- **Test structure**: 337 existing tests in `tests/` directory mirroring `src/agentdk/`
- **Environment patterns**: Examples exist in `examples/integration_test.py` and `adk-python/tests/`

### Implementation Gaps ❌
- **No tests currently use `@pytest.mark.integration`**
- **No conditional execution** based on API key availability
- **No end-to-end agent session tests**
- **Integration tests would fail** without OPENAI_API_KEY

## 📋 Implementation Tasks

### Phase 1: Core Integration Test Framework

#### Task 1: Create Integration Test Directory Structure
```bash
examples/
├── integration_test/
│   ├── __init__.py
│   ├── conftest.py                    # Shared fixtures and configuration
│   ├── test_agent_sessions.py         # Main integration tests
│   └── test_subagent_functionality.py # Sub-agent specific tests
```

#### Task 2: Implement Environment-Aware Test Configuration
**File:** `examples/integration_test/conftest.py`

```python
import pytest
import os
from typing import Optional

def pytest_configure(config):
    """Add integration test markers and configuration."""
    config.addinivalue_line(
        "markers", 
        "integration: marks tests as integration tests requiring API keys"
    )

@pytest.fixture(scope="session")
def openai_api_key() -> Optional[str]:
    """Fixture to provide OPENAI_API_KEY or skip tests."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set - skipping integration test")
    return api_key

@pytest.fixture(scope="session") 
def agent_examples_path():
    """Path to agent examples for testing."""
    return "examples/agent_app.py"

@pytest.fixture(scope="session")
def eda_agent_path():
    """Path to EDA agent example for testing.""" 
    return "examples/subagent/eda_agent.py"
```

#### Task 3: Implement Core Integration Tests
**File:** `examples/integration_test/test_agent_sessions.py`

Key test methods:
- `test_fresh_agent_session()`: Fresh session start verification
- `test_session_resumption()`: Resume functionality with `--resume`
- `test_memory_learning_correction()`: Memory persistence and learning
- `test_session_management_commands()`: CLI session commands

#### Task 4: Update Default Test Execution
**File:** `pytest.ini` (modify existing)

```ini
[tool:pytest]
testpaths = tests
addopts = -m "not integration" --strict-markers -v
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests requiring API keys (deselect with '-m "not integration"')
    unit: marks tests as unit tests
```

### Phase 2: Test Implementation Details

#### Test Scenarios Implementation

**Test 1: Fresh Session Start**
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_fresh_agent_session(openai_api_key, agent_examples_path):
    """Test fresh agent session without prior context."""
    # Implementation with subprocess calls and output verification
    # Verify: no previous context, table listing, customer count
```

**Test 2: Session Resumption**
```python  
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_session_resumption(openai_api_key, agent_examples_path):
    """Test session resumption with --resume flag."""
    # Implementation with session preparation and resume testing
    # Verify: previous context maintained, memory persistence
```

**Test 3: Memory Learning**
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set") 
def test_memory_learning_correction(openai_api_key, agent_examples_path):
    """Test memory learning and user correction scenarios."""
    # Implementation with case sensitivity testing and learning verification
```

**Test 4: Sub-agent Functionality**
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_subagent_functionality(openai_api_key, eda_agent_path):
    """Test EDA sub-agent with same scenarios."""
    # Implementation testing EDA agent specific functionality
```

### Phase 3: Test Execution and CI Integration

#### Task 5: Modify Existing Unit Tests
Add `@pytest.mark.unit` to appropriate existing tests that don't require external dependencies.

#### Task 6: Update Documentation
**Files:** `CLAUDE.md`, `README.md`

Add sections for:
- Integration test execution commands
- Environment setup requirements
- CI/CD pipeline considerations

#### Task 7: CI Configuration Updates
Ensure CI pipelines handle both test types appropriately:
- Default runs exclude integration tests
- Separate CI job for integration tests with API keys
- Clear separation of unit vs integration test results

## 🔧 Technical Implementation Details

### Test Execution Commands
```bash
# Default: Run only unit tests (new behavior)
python -m pytest tests/ -v

# Explicit: Run unit tests only
python -m pytest tests/ -v -m "unit"

# Run integration tests (requires OPENAI_API_KEY)
python -m pytest examples/integration_test/ -v -m integration

# Run all tests including integration
python -m pytest tests/ examples/integration_test/ -v

# Run specific integration test
python -m pytest examples/integration_test/test_agent_sessions.py::test_fresh_agent_session -v
```

### Expected Test Output Verification
Tests will verify specific patterns in CLI output:
- **Table names**: "customers", "accounts", etc.
- **Numeric counts**: Regex patterns for customer counts
- **Memory context**: Previous table access information
- **Error handling**: Graceful failure scenarios

### Environment Variable Management
- **Required**: `OPENAI_API_KEY` for LLM integration
- **Optional**: `ANTHROPIC_API_KEY` for alternative LLM testing
- **Test isolation**: Each test runs in clean environment
- **Session cleanup**: Automatic cleanup between tests

## ✅ Acceptance Criteria Verification

- [ ] Integration tests tagged with `@pytest.mark.integration`
- [ ] Tests skip gracefully when `OPENAI_API_KEY` not available  
- [ ] Default `pytest` run excludes integration tests
- [ ] Integration tests executable with `pytest -m integration`
- [ ] End-to-end agent session tests covering all 4 scenarios
- [ ] Result verification with keyword/pattern matching
- [ ] Documentation updated with execution instructions
- [ ] CI configuration handles both test types

## 🚀 Implementation Timeline

### Immediate (Today)
1. Create integration test directory structure
2. Implement basic test framework with environment detection
3. Create first integration test (fresh session)

### Phase 1 (1-2 days)
1. Complete all 4 core integration test scenarios
2. Update pytest configuration for default exclusion
3. Add comprehensive output verification

### Phase 2 (2-3 days)  
1. Add unit test markers to existing tests
2. Implement sub-agent specific tests
3. Update documentation and examples

### Phase 3 (Final)
1. CI configuration updates
2. Final testing and verification
3. PR creation and review

## 📝 Success Metrics

1. **Developer Experience**: Tests don't fail due to missing API keys
2. **CI Performance**: Default test runs are faster (unit tests only)
3. **Coverage**: Critical end-to-end workflows are validated
4. **Flexibility**: Selective test execution based on available resources
5. **Reliability**: Integration tests accurately verify agent functionality

## 🔗 Dependencies

- Existing pytest configuration (✅ already available)
- Agent examples in `examples/agent_app.py` and `examples/subagent/eda_agent.py`
- CLI functionality (`agentdk run` command)
- Session management system
- Memory persistence functionality

## 📋 Risk Mitigation

- **API Rate Limits**: Use test-specific prompts and minimal interactions
- **Test Isolation**: Each test starts with clean state
- **Environment Consistency**: Clear environment variable requirements
- **Flaky Tests**: Robust output verification with multiple assertion methods
- **Maintenance**: Clear documentation for test updates and debugging