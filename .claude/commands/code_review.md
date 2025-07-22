# Code Review Command

## Purpose
Comprehensive code review workflow that integrates with GitHub issues, provides systematic analysis, and ensures quality through structured testing and validation.

## Usage
```bash
# For GitHub issues
code_review --issue 123
code_review --issue https://github.com/owner/repo/issues/123

# For standalone code review (no GitHub issue)
code_review --files "src/**/*.py" 
code_review --directory "src/agents/"
```

## Core Review Process

### 1. Issue Context and Discovery
```markdown
**GitHub Issue Workflow**:
- Use `gh issue view <number>` to get detailed issue information
- Link issue to PR: `gh pr create --title "Fix #123: <description>" --body "Fixes #123"`
- Search for related issues: `gh issue list --search "keyword"`
- Review issue history and previous attempts

**Non-GitHub Issue Scenarios**:
- Direct file/directory analysis for general code quality
- Legacy code audits without specific issues
- Pre-commit review processes
- Proactive security audits

**Analysis Categories**:
- 🔴 **Critical**: Security vulnerabilities, breaking bugs, major performance issues
- 🟠 **High**: Significant code quality issues, architectural problems
- 🟡 **Medium**: Minor bugs, style inconsistencies, missing tests
- 🟢 **Low**: Documentation improvements, minor optimizations

**Specific Areas to Review**:
- Security vulnerabilities and potential attack vectors
- Performance bottlenecks and optimization opportunities
- Code quality issues (readability, maintainability, complexity)
- Best practices violations for specific language/framework
- Bug risks and potential runtime errors
- Architecture concerns and design pattern improvements
- Testing gaps and test quality issues
- Documentation deficiencies
```

### 2. Planning with TodoWrite
```markdown
**TodoWrite Management**:
1. **Read ALL Issues**: Thoroughly understand every issue before starting fixes
2. **Create TodoWrite List**: Categorize with severity-based priorities
3. **Group Related Issues**: Identify issues that should be fixed together
4. **Identify Dependencies**: Determine which fixes depend on others
5. **Break Down Complex Tasks**: Split large issues into manageable sub-tasks

**GitHub Integration**:
- Create branch: `git checkout -b fix-issue-123`
- Reference issue in commits: `git commit -m "fix: address memory leak in agent.py (fixes #123)"`
- Link PR to issue: Include "Fixes #123" in PR description
```

### 3. Implementation Strategy
```markdown
**Priority Order**: Always fix critical/high-priority issues first

**One Task at a Time**:
- Mark TodoWrite task as "in_progress" before starting
- Complete the entire fix before moving to next task
- Test each fix individually before proceeding
- Mark "completed" immediately after finishing each task

**Documentation**: Explain what was changed and why for each fix
```

### 4. Testing and Validation
```markdown
**Individual Testing**: Test each fix as it's completed

**Full Test Suite**: Run complete test suite after all fixes
- Command: `python -m pytest tests/ -v`
- ALL tests must pass before proceeding

**Code Formatting**: Apply consistent formatting
- `black src/ tests/ examples/`
- `isort src/ tests/ examples/`

**Performance Validation**: Measure improvements where applicable
```



### 5. Final Verification and GitHub Integration
```markdown
**Verification**:
- Verify all issues resolved
- Check for side effects and new issues
- Ensure tests pass and code is formatted

**GitHub Workflow**:
- Commit with descriptive message referencing issue
- Push branch: `git push -u origin fix-issue-123`
- Create PR: `gh pr create --title "Fix #123: <description>" --body "Fixes #123"`
- Request review if needed

**For Non-GitHub Reviews**:
- Create comprehensive commit with detailed message
- Document performance improvements
- Include co-authorship attribution
```

## Quality Standards and Review Guidelines

### Be Specific and Actionable
```markdown
✅ GOOD: "Extract the 50-line validation function in `UserService.py:120-170` into a separate `ValidationService` class"
❌ BAD: "Code is too complex"

✅ GOOD: "Fix SQL injection vulnerability in `src/auth/login.py:45-52` by using parameterized queries"
❌ BAD: "Security issue found"
```

### Include Context and Rationale
```markdown
- Explain *why* something needs to be changed
- Suggest specific solutions or alternatives
- Reference relevant documentation or best practices
- Consider the effort-to-benefit ratio of suggestions
```

### Language/Framework Specific Checks
```markdown
- Apply appropriate linting rules and conventions
- Check for framework-specific anti-patterns
- Validate dependency usage and versions
- Ensure proper typing annotations (Python)
- Verify centralized prompt management (AgentDK)
```

## Exception Handling Decision Framework

### Critical Dependencies (FAIL FAST)
```python
# Let ImportError propagate for required functionality
from required_lib import CriticalClass

def __init__(self, config: Required[Config]):
    if not config.required_setting:
        raise AgentInitializationError("Required configuration missing")
```

### Optional Features (GRACEFUL DEGRADATION)
```python
# Handle optional dependencies gracefully
try:
    from optional_lib import Enhancement
    self.enhancement = Enhancement()
except ImportError:
    logger.info("Enhancement not available - continuing with core functionality")
    self.enhancement = None
```

## TodoWrite Template for Code Reviews

```python
todos = [
    {
        "id": "fix_critical_security",
        "content": "Fix SQL injection vulnerability in query builder (src/auth/login.py:45-52)",
        "status": "pending",
        "priority": "high"
    },
    {
        "id": "remove_deprecated_method", 
        "content": "Remove deprecated _run_query_in_new_loop method causing session corruption",
        "status": "pending",
        "priority": "high"
    },
    {
        "id": "improve_error_logging",
        "content": "Enhance error handling with detailed messages and fail-fast for critical deps", 
        "status": "pending",
        "priority": "medium"
    },
    {
        "id": "fix_status_logging",
        "content": "Update status logging to use 'successful' vs 'failed' instead of 'completed'",
        "status": "pending", 
        "priority": "medium"
    }
]
```

## Task Format for GitHub Issues

```markdown
## 🔴 Critical Priority
- [ ] **[SECURITY]** Fix SQL injection vulnerability in `src/auth/login.py:45-52`
- [ ] **[BUG]** Handle null pointer exception in `utils/parser.py:120`

## 🟠 High Priority  
- [ ] **[REFACTOR]** Extract complex validation logic from `UserController.py` into separate service
- [ ] **[PERFORMANCE]** Optimize database queries in `reports/generator.py`

## 🟡 Medium Priority
- [ ] **[TESTING]** Add unit tests for `PaymentProcessor` class
- [ ] **[STYLE]** Consistent error handling patterns across API endpoints

## 🟢 Low Priority
- [ ] **[DOCS]** Add docstrings to public API methods
- [ ] **[CLEANUP]** Remove unused imports in `components/` directory
```


## Performance Validation Checklist

- [ ] Measure before/after performance for session-related fixes
- [ ] Document specific improvements (e.g., "3.114s → 2.166s improvement (30% faster)")
- [ ] Verify persistent sessions working correctly
- [ ] Check for any performance regressions in unrelated areas

## Anti-Patterns to Avoid

### ❌ Critical Anti-Patterns
```python
# ❌ Silent Exception Swallowing (Fail-Fast Violation)
def _load_tools(self) -> None:
    try:
        self.tools = load_external_tools()
    except Exception as e:
        logger.error(f"Failed to load tools: {e}")
        # Continues with broken state - WRONG!

# ❌ Hardcoded Prompts (Centralization Violation)
class Agent:
    def get_prompt(self):
        return "You are an agent..."  # Should be in prompts.py

# ❌ Code Duplication (Inheritance Violation)
class Agent1:
    def __init__(self, llm=None, config=None):
        # 20+ lines of common setup - duplicated across agents

# ❌ Bypassing Abstraction (Integrity Violation)
class Client:
    def do_work(self, data):
        # Client manipulating provider's internals directly
        self.provider.component_a.process(data)
        self.provider.component_b.update(data)
```

### ❌ Process Anti-Patterns
- Don't mute ImportError for critical dependencies (violates fail-fast principle)
- Don't keep deprecated methods that cause session corruption
- Don't use vague status logging like "completed" vs "successful/failed"  
- Don't commit without testing all changes first
- Don't fix issues in random order - always prioritize systematically
- Don't batch todo completions - mark each complete immediately
- Don't duplicate existing tasks or ignore TASK.md updates

### ✅ Quality Standards
```python
# ✅ Proper Exception Handling with Fail-Fast
def _load_tools(self) -> None:
    try:
        self.tools = load_external_tools()
    except Exception as e:
        logger.error(f"Failed to load tools: {e}")
        raise  # Let caller decide if acceptable

# ✅ Centralized Prompt Management
from .prompts import get_agent_prompt

class Agent:
    def _get_default_prompt(self) -> str:
        return get_agent_prompt()  # Externalized

# ✅ Inheritance Over Implementation
class BaseAgent(ABC):
    def __init__(self, llm=None, config=None):
        # Common setup logic centralized
        
    @abstractmethod
    def _get_default_prompt(self) -> str:
        pass

# ✅ Abstraction Integrity
class Client:
    def do_work(self, data):
        # Use provider's high-level API only
        self.provider.high_level_api_method(data)
```

### ✅ Process Standards
- Use TodoWrite systematically for tracking multiple issues
- Apply fail-fast principle for critical dependencies
- Test each fix individually and run full test suite
- Format code consistently with project standards
- Document performance improvements with measurements
- Create single comprehensive commit with detailed message
- Always include typing annotations and docstrings (Python)
- Use pytest exclusively (not unittest module)
- Maintain proper directory structure with tests/ mirroring src/

## Trigger Conditions

Load this command when:
- `error.txt` or similar code review files are mentioned
- Multiple code issues need systematic fixes  
- Dealing with exception handling in critical paths
- Implementing fail-fast vs graceful degradation patterns
- Code review tasks require structured approach
- Performance improvements need validation

## Success Metrics

- All original issues documented and resolved
- Tests passing after each individual fix
- Tests passing after all fixes applied
- Code consistently formatted
- Performance improvements measured and documented
- Single comprehensive commit created
- No new issues introduced
