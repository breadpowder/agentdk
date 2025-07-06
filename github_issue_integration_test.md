We need to run integration test to cover agent session end-to-end. This needs to run to ensure the basic end-to-end works with memory settings. Test cases must and only include below scenarios.


1. the global agent flow start from fresh.
agentdk run examples/agent_app.py

then run 
0. "which table you last accessed" - expect nothing
1. "list table" - expect list all tables
2. "how many customers you have" - except run query on customer table and have X count

expect answers and answers must be fixed


2. start global agent with resume.
agentdk run examples/agent_app.py --resume
then run
which table i just accessed? - expect customer table
which query i just run? -expect the query you just run which count customer table


3. session memory works can correct from user input 
You need to display memory before and after test for debuggin and obserability.
agentdk run examples/agent_app.py 
 -  "which table you last accessed" - expect nothing
 -  "what the average amout from chequing account" - except select accout type low case chequing and get noting
-  then user correct the query with case insentive - query works
-  "what the max amount from saving account"  - query works beause learned from experience


for the same thing run eda_subagent and ensure it work well.


