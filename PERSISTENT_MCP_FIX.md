# Persistent MCP Session Fix
## Problem Summary
The original `langchain-mcp-adapters` implementation (see class MultiServerMCPClient in client.py) suffered from a critical architectural issue:
- **MCP servers terminated after each tool call** due to ephemeral subprocess sessions
- **Performance overhead** of constant process creation/destruction (50ms+ per call)

## Goal in examples/

Exapmple:
```python
from agentdk.utils.utils import llm
from subagent.eda_agent import EDAAgent
agent = EDAAgent(llm=llm) 
agent.query("query1")  
agent.query("query2")  # reuse session
agent.query("query3")  # reuse session

# Sessions cleaned up automatically after program is done
```

## Requirement
Functional 
1. You can use python shutdown hook to clean up resource
2. Lifecycles of the tool needs to coupled with agent
3. Implementation must be in @agentdk without modifying `langchain-mcp-adapters` this is a 3rd party library. Extra structure can be created to achieve code modularity, However. all classes implement SubAgentInterface MUST have the capability when using mcp server
4. Honor the async pattern `ensure_nest_asyncio()` defined in class subagent SubAgentInterface.  We need to ensure the solution works in IPython as well. The async interaction needs to be hidden from client side
5. Must use query as the agent call entry_point
6. Test script must be in /examples and run test to ensure it get fixed
