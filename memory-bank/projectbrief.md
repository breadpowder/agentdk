# AgentDK Project Brief

## Project Overview
Creating an AgentDK project with main logic in `src/agentdk` for pip distribution. The project includes:
- Core package for pip installation
- Examples folder for sub-agents and agents depending on MCP servers
- Async pattern support for IPython/Jupyter environments

## Key Requirements
1. **Async Pattern**: Application runs in IPython/Jupyter, maintain async patterns
2. **Centralized Logging**: Initialize logging at project level (INFO default)
3. **MCP Integration**: Offload logic from eda_agent to agent_interface definitions
4. **Testing Setup**: MySQL docker with sample data (customer, transaction, account tables)

## Main Components
- `src/agentdk/` - Main package for pip distribution
- `examples/` - Sub-agents and agent implementations
- MCP server integration with mysql_mcp_server reference
- Agent interface with initialization and MCP server loading

## Target Usage Pattern
```python
eda_agent = EDAAgent(llm=llm, prompt=prompt_defined)
workflow = create_supervisor([research_agent, eda_agent], model=model, prompt=...)
```
