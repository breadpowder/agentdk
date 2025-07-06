### Command run and output
(agentdk) zineng@zineng-Dell-Tower-Plus:~/workspace/agentic/agentdk$ agentdk run examples/subagent/eda_agent.py
Loading agent from /home/zineng/workspace/agentic/agentdk/examples/subagent/eda_agent.py...
✅ Using OpenAI gpt-4o-mini
No LLM specified, attempting to use available LLM...
✅ Using OpenAI gpt-4o-mini
Agent 'eda_agent' ready. Type 'exit' to quit, 'help' for commands.
Started new session for eda_agent
[user]: which table you have access to?
[eda_agent]: {'messages': [AIMessage(content='No input provided', additional_kwargs={}, response_metadata={})]}


### issues
1. The message must be ONLY show content for readability.

2. eda agent failed to provide content. something is wrong for the flow require debug.

3. [user]: ^C (i enter ^C for interrupt)
Gracefully shutting down...
Problem: control c does not shutdown the agent


