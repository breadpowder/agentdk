







you to create agentDK project the main logic is on the src/agentdk which I need to put it on pip central so people can install it.
examples/folder is to define sub-agents and agent which can depends on MCP server 

Rules: 
0. The application needs to run ipython. i.e. jupternotebook as so it expect async pattern don't change the sync and async unless you are confident.
1. the loggin needs to be initialized in the centralized project level instead of split in each concrete class. Set the default logger to be INFO
2. Offload the current logics from ead_agent to the agent_interface definitions, including initialization process and wrapped tooling logic which is to trace the MCP server coding.

Some refactoring idea:
core/
    Add mcp_load.py 
        - load mcp conf get_mcp_config(self) -> Dict[str, Any]: 
        * remove the logging part and needs to do basic validation of conf

    Offload eda_agent.py    
        a. async def _initialize(self) -> 
            None: this needs to be in class SubAgentInterface(AgentInterface) 

        b.   When sub-agent creates, it calls __initiate() function to load MCP servers. Each agent initialze accept parametrer pf a llm, mcp conf
         load its own conf,the default path is the agent location with mcp_config.json and system prompt. 



For eda_agent.py in examples/,to be a very straightforward impl  plus a system prompt file.py in examples/ folder. 
For subagent, checkout https://github.com/designcomputer/mysql_mcp_server under /examples as a mcp server and integrate with it
    
1. Any reason you repliace code betwe@eda_agent.py and paraneter class in @agent_interface.py   ? You need to refactor @eda_agent.py  , don't replicate code using  the same implement from  SubAgentInterface FOR METHODS _query_async,  _initialize(self), _setup_mcp_client(self), _load_tools,_get_tools_from_mcp,_wrap_tools_with_logging and some other method as well. ALWAY resuse unless you MUST to.  


 2. _get_default_prompt(self) -> str:@eda_agent.py  
 3. you did not follow instruction in @design_doc.md  to crate a top level agent.py in @/examples  
 
 4. you did not follow instruction to start a mysql and popuate table and doc in @design_doc.md 

