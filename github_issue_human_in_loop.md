# [Feature] Agent: Add Human-in-the-Loop Support for Interactive Decision Making

## Summary
- **One-sentence description**: Add human-in-the-loop capabilities to AgentDK for interactive decision making and fallback scenarios
- **Impact level**: High
- **Component affected**: Agent/Core

## Problem Statement
- **Current limitations**: AgentDK currently lacks human-in-the-loop functionality, limiting interactive capabilities when critical decisions need human input or when agents fail repeatedly
- **Use cases**: 
  1. Critical decision points requiring human judgment
  2. Fallback mechanism when subagents fail multiple times (e.g., tool calling failures)
  3. Post-resolution human feedback integration into agent memory
- **Business value**: Enhances agent reliability, user control, and learning capabilities through human feedback

## Technical Requirements
- **Core functionality**: 
  - Human input prompts at critical decision points
  - Fallback mechanisms for failed operations
  - Checkpoint system for execution resumption after human feedback
  - Memory integration for human feedback
- **Implementation scope**: Both agent and sub-agent levels in `src/agentdk`
- **Integration**: Seamless integration with existing agents without extra configuration work
- **Dependencies**: Leverage LangGraph features (ToolNode, loops, conditional edges, retry policy, time travel checkpoints)

## Acceptance Criteria
- [ ] Human-in-the-loop functionality available at agent level
- [ ] Human-in-the-loop functionality available at sub-agent level  
- [ ] Checkpoint system supports execution resumption after human feedback
- [ ] Fallback mechanism triggers after configurable number of failures
- [ ] Human feedback can be integrated into agent memory
- [ ] Seamless integration with existing agents (no breaking changes)
- [ ] Documentation and examples provided
- [ ] Tests covering all human-in-the-loop scenarios