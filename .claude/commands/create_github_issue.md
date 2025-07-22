# GitHub Issue Creation Template

Use this template to create comprehensive GitHub issues for the AgentDK project. Select the appropriate issue type and follow the corresponding template section.

## Pre-Issue Checklist (All Types)
- [ ] Is this a duplicate of an existing issue?
- [ ] Have you searched the repository for similar issues?
- [ ] Do you have sufficient details to provide?
- [ ] Is this the right repository for this issue?

## Issue Classification
Select ONE issue type and follow the corresponding template below:

- **Bug Report**: Something isn't working as expected
- **Feature Request**: New functionality request
- **Enhancement**: Improvement to existing functionality
- **Documentation**: Documentation improvements
- **Performance**: Performance-related issues
- **Security**: Security-related concerns

## Title Format Guidelines
- **Bug**: `[Bug] Component: Brief description`
- **Feature**: `[Feature] Component: Brief description`
- **Enhancement**: `[Enhancement] Component: Brief description`
- **Documentation**: `[Docs] Component: Brief description`
- **Performance**: `[Performance] Component: Brief description`
- **Security**: `[Security] Component: Brief description`

---

# BUG REPORT TEMPLATE

## Summary
- **One-sentence description** of the bug
- **Impact level**: Critical/High/Medium/Low
- **Component affected**: Agent/Memory/MCP/Core/etc.

## Environment Details
```
AgentDK Version: [version]
Python Version: [version]
Operating System: [OS and version]
Dependencies: [relevant package versions]
```

## Reproduction Steps
1. **Prerequisites**: What setup is required?
2. **Steps**: Numbered list of exact steps to reproduce
3. **Expected Result**: What should happen?
4. **Actual Result**: What actually happens?
5. **Frequency**: Always/Sometimes/Rarely

## Code Examples
```python
# Minimal reproducible example
# Include relevant configuration
# Remove sensitive information
```

## Logs/Error Messages
```
# Include relevant error logs
# Use code blocks for formatting
# Include timestamps if helpful
```

## Additional Context
- **Files involved**: List relevant files
- **Configuration**: Relevant config snippets
- **Workarounds**: Any temporary solutions found
- **Related issues**: Link to related issues

## Bug-Specific Commands
```bash
# Check AgentDK version
python -c "import agentdk; print(agentdk.__version__)"

# Run specific test
python -m pytest tests/specific_test.py -v

# Check dependencies
uv tree

# Generate logs
python your_script.py 2>&1 | tee issue_logs.txt
```

---

# FEATURE REQUEST TEMPLATE

## Summary
- **One-sentence description** of the feature
- **Impact level**: Critical/High/Medium/Low
- **Component affected**: Agent/Memory/MCP/Core/etc.

## Problem Statement
- **Current limitations**: What can't be done today?
- **Use cases**: Who needs this and why?
- **Business value**: What problem does this solve?

## Proposed Solution
- **High-level approach**: How should this work?
- **User experience**: How will users interact with this?
- **Integration points**: How does this fit with existing features?

## Technical Requirements
- **Core functionality**: What must be implemented?
- **Dependencies**: What new libraries or tools are needed?
- **Integration analysis**: Compare different approaches/technologies if applicable

## Acceptance Criteria
- [ ] Functional requirement 1
- [ ] Functional requirement 2
- [ ] Non-functional requirement 1
- [ ] Documentation provided
- [ ] Tests passing

**Note**: Focus on requirements and analysis points rather than implementation details, code samples, API designs, performance targets, security specifics, or implementation planning. These should be addressed during the development planning phase.

---

# ENHANCEMENT TEMPLATE

## Summary
- **One-sentence description** of the enhancement
- **Impact level**: Critical/High/Medium/Low
- **Component affected**: Agent/Memory/MCP/Core/etc.

## Current Behavior
- **What exists today**: Description of current functionality
- **Pain points**: What makes current approach problematic?
- **Limitations**: What can't be done with current approach?

## Desired Behavior
- **Improved functionality**: What should change?
- **Benefits**: How will this improve the user experience?
- **Success metrics**: How will we measure improvement?

## Integration Analysis
- **Current approach**: How is this currently handled?
- **Alternative approaches**: What other options exist?
- **Technology comparison**: Pros/cons of different solutions if applicable

## Acceptance Criteria
- [ ] Enhanced functionality works as described
- [ ] Documentation updated
- [ ] Tests passing

**Note**: Focus on requirements and comparative analysis rather than implementation details, performance targets, migration specifics, or detailed compatibility planning. These should be addressed during the development planning phase.

---

# DOCUMENTATION TEMPLATE

## Summary
- **Documentation type**: API/Tutorial/Guide/Reference
- **Target audience**: Developers/Users/Contributors
- **Component affected**: Agent/Memory/MCP/Core/etc.

## Missing/Incorrect Documentation
- **What's missing**: Specific gaps in documentation
- **What's incorrect**: Outdated or wrong information
- **Impact**: How does this affect users?

## Proposed Content
- **Structure**: Outline of proposed documentation
- **Examples**: Code examples to include
- **Diagrams**: Any diagrams or visuals needed

## Target Audience
- **Primary users**: Who will use this documentation?
- **Skill level**: Beginner/Intermediate/Advanced
- **Context**: When will they need this information?

## Acceptance Criteria
- [ ] Documentation covers all specified topics
- [ ] Examples are working and tested
- [ ] Content is clear and well-structured
- [ ] Reviewed by target audience member

---

# PERFORMANCE TEMPLATE

## Summary
- **Performance issue**: What's slow or resource-intensive?
- **Impact level**: Critical/High/Medium/Low
- **Component affected**: Agent/Memory/MCP/Core/etc.

## Current Performance
- **Metrics**: Current performance measurements
- **Benchmarks**: Baseline performance data
- **Bottlenecks**: Identified performance bottlenecks

## Expected Performance
- **Target metrics**: What performance is expected?
- **Improvement goals**: Specific improvement targets
- **Constraints**: Any performance constraints?

## Profiling Data
```
# Include profiling output
# Memory usage data
# CPU usage data
```

## Acceptance Criteria
- [ ] Performance meets target metrics
- [ ] No regression in other areas
- [ ] Changes are measurable and documented
- [ ] Performance tests added

---

# SECURITY TEMPLATE

## Summary
- **Security concern**: Type of security issue
- **Impact level**: Critical/High/Medium/Low
- **Component affected**: Agent/Memory/MCP/Core/etc.

## Security Impact
- **Vulnerability type**: What type of security issue?
- **Attack vector**: How could this be exploited?
- **Affected users**: Who is impacted?

## Mitigation Requirements
- **Immediate actions**: What can be done right now?
- **Long-term solutions**: What's the proper fix?
- **Workarounds**: Any temporary mitigations?

## Disclosure Timeline
- **Discovery date**: When was this identified?
- **Disclosure plan**: How should this be handled?
- **Coordination**: Who needs to be involved?

## Acceptance Criteria
- [ ] Security vulnerability is resolved
- [ ] No new security issues introduced
- [ ] Security testing completed
- [ ] Disclosure process followed

---

# COMMON SECTIONS (All Types)

## Priority Guidelines
- **Critical**: System unusable, data loss, security vulnerability
- **High**: Major functionality broken, significant impact
- **Medium**: Minor functionality issues, inconvenience
- **Low**: Cosmetic issues, nice-to-have improvements

## Labels to Consider
- **Type**: `bug`, `enhancement`, `feature`, `documentation`, `performance`, `security`
- **Component**: `memory`, `mcp`, `agent`, `core`, `testing`, `cli`
- **Priority**: `priority:high`, `priority:medium`, `priority:low`
- **Community**: `good-first-issue`, `help-wanted`

## Issue Submission Workflow

1. **Prepare**: Gather all required information for your issue type
2. **Create**: Write issue using appropriate template section
3. **Review**: Check for completeness and clarity
4. **Confirm**: User confirms the issue content is ready
5. **Submit**: Create GitHub issue using `gh` command
6. **Follow-up**: Respond to maintainer questions promptly
7. **Verify**: Test proposed fixes when available

## Creating the GitHub Issue

Once the user has confirmed the issue file is ready, proceed with creating the issue:

### Step 1: Review the Issue File
```bash
# Display the issue file for user review
cat github_issue_[name].md
```

### Step 2: Confirm with User
Ask the user: "Are you ready to create this GitHub issue? (y/n)"

### Step 3: Create the Issue
```bash
# Create the issue using GitHub CLI
gh issue create --title "$(head -1 github_issue_[name].md | sed 's/^# //')" --body-file github_issue_[name].md

# Alternative: Create issue with labels
gh issue create --title "$(head -1 github_issue_[name].md | sed 's/^# //')" --body-file github_issue_[name].md --label "feature,cli,priority:medium"
```

### Step 4: Verify Issue Creation
```bash
# List recent issues to confirm creation
gh issue list --limit 5

# View the created issue
gh issue view [issue-number]
```

### GitHub CLI Setup (if needed)
```bash
# Install GitHub CLI (if not already installed)
# macOS: brew install gh
# Ubuntu: sudo apt install gh

# Authenticate with GitHub
gh auth login

# Check authentication status
gh auth status
```

## Quick Reference Commands

### Environment Information
```bash
# Check AgentDK version
python -c "import agentdk; print(agentdk.__version__)"

# Check Python version
python --version

# Check installed packages
pip list | grep -E "(agentdk|langchain|openai)"
```

### Testing Commands
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/specific_test.py -v

# Run with coverage
python -m pytest tests/ --cov=agentdk
```

### Debugging Commands
```bash
# Generate debug logs
python your_script.py 2>&1 | tee debug_logs.txt

# Check dependency tree
uv tree

# Validate configuration
python -c "import json; print(json.load(open('config.json')))"
```