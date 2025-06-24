# AgentDK - Agent Development Kit for LangGraph + MCP Integration

A powerful Python framework for building intelligent agents using LangGraph and Model Context Protocol (MCP) integration. AgentDK simplifies the creation of multi-agent systems with standardized tool access, data exploration capabilities, and workflow orchestration.

## 🚀 Key Features

- **🤖 Multi-Agent Architecture**: Build sophisticated agent systems using LangGraph supervisor patterns
- **🔌 MCP Integration**: Seamless integration with Model Context Protocol servers for standardized tool access
- **📊 Specialized Agents**: Pre-built EDA (Exploratory Data Analysis) and Research agents
- **🛠️ Rich Tool Ecosystem**: Easy integration with databases, filesystems, web search, and more
- **🔄 Async Support**: Full async/await support for scalable agent operations
- **📝 Type Safety**: Built with Pydantic v2 for robust data validation and type safety
- **🎯 Production Ready**: Comprehensive testing, logging, and error handling

## 📦 Installation

```bash
# Install from PyPI
pip install agentdk

# Install with optional dependencies
pip install agentdk[openai]     # For OpenAI models
pip install agentdk[anthropic]  # For Anthropic models
pip install agentdk[all]        # All optional dependencies
```

## 🏁 Quick Start

### 1. Simple Agent Creation

```python
from agentdk import EDAAgent
from langchain_openai import ChatOpenAI

# Create an LLM model
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Create an EDA agent with database access
agent = EDAAgent(
    llm=llm,
    mcp_config_path="path/to/mcp_config.json"  # MCP server configuration
)

# Query your data
result = agent.query("What tables are available in the database?")
print(result)
```

### 2. Agent with Custom Prompts

```python
from agentdk import EDAAgent
from agentdk.prompts import get_eda_agent_prompt

# Use centralized prompts
agent = EDAAgent(
    llm=llm,
    prompt=get_eda_agent_prompt(),  # Pre-configured EDA prompt
    mcp_config_path="mcp_config.json"
)

# Analyze your data
result = agent.query("What is the total transaction amount for customer 'John Smith'?")
print(result)
```

### 3. Async Usage

```python
import asyncio
from agentdk import EDAAgent

async def analyze_data():
    agent = EDAAgent(llm=llm, mcp_config_path="mcp_config.json")
    
    # Multiple concurrent queries
    tasks = [
        agent.query_async("Show me all tables"),
        agent.query_async("Count total customers"),
        agent.query_async("Show recent transactions")
    ]
    
    results = await asyncio.gather(*tasks)
    return results

# Run async analysis
results = asyncio.run(analyze_data())
```

## 🏗️ Multi-Agent Systems

### Creating a Supervisor Agent

```python
from agentdk import Agent, EDAAgent, ResearchAgent
from langchain_openai import ChatOpenAI

# Create LLM
llm = ChatOpenAI(model="gpt-4")

# Create a supervisor that manages multiple specialized agents
supervisor = Agent(llm)

# The supervisor automatically routes queries to the right agent:
# - Data questions → EDA Agent (with database access)
# - Research questions → Research Agent (with web search)

# Example usage
data_result = supervisor("What is the average transaction amount?")
research_result = supervisor("What are the latest AI trends in 2024?")
```

### Building Custom Multi-Agent Workflows

```python
from agentdk import EDAAgent, ResearchAgent
from agentdk.prompts import get_supervisor_prompt

# Create specialized agents
eda_agent = EDAAgent(
    llm=llm,
    mcp_config_path="database_config.json",
    name="data_analyst"
)

research_agent = ResearchAgent(
    llm=llm,
    tools=[web_search_tool],
    name="researcher"
)

# Create supervisor with custom routing
supervisor = Agent(
    llm=llm,
    agents=[eda_agent, research_agent],
    prompt=get_supervisor_prompt()  # Intelligent routing logic
)

# Complex multi-step analysis
result = supervisor("""
Analyze our customer transaction data and research industry benchmarks 
to provide insights on our performance compared to competitors.
""")
```

## 🔧 MCP Integration

### Setting Up MCP Servers

MCP (Model Context Protocol) servers provide standardized tool access. Here's how to configure them:

#### 1. Database MCP Server

```json
// mcp_config.json
{
  "servers": {
    "mysql": {
      "command": "python",
      "args": ["-m", "mysql_mcp_server"],
      "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "your_user",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_DATABASE": "your_database"
      }
    }
  }
}
```

#### 2. Using the Database Agent

```python
from agentdk import EDAAgent

# Agent automatically loads MCP tools
agent = EDAAgent(
    llm=llm,
    mcp_config_path="mcp_config.json"
)

# SQL queries are executed through MCP
result = agent.query("Show me the top 10 customers by transaction volume")
```

### Available MCP Servers

| Server Type | Description | Use Case |
|-------------|-------------|----------|
| **MySQL** | Database queries | Data analysis, reporting |
| **PostgreSQL** | Database queries | Data analysis, reporting |
| **Filesystem** | File operations | File management, data processing |
| **Web Search** | Search engines | Research, information gathering |
| **APIs** | REST/GraphQL | External service integration |

### Custom MCP Tools

```python
from agentdk import EDAAgent

def custom_tool(query: str) -> str:
    """Custom business logic tool."""
    # Your custom implementation
    return f"Processed: {query}"

# Add custom tools to agent
agent = EDAAgent(
    llm=llm,
    tools=[custom_tool],  # Additional tools
    mcp_config_path="mcp_config.json"  # Plus MCP tools
)
```

## 🎯 Agent Types

### EDA Agent (Data Analysis)

Perfect for database analysis and SQL queries:

```python
from agentdk import EDAAgent

agent = EDAAgent(
    llm=llm,
    mcp_config_path="database_config.json"
)

# Automatic SQL generation and execution
result = agent.query("What are our top 5 products by revenue this quarter?")
```

**Features:**
- ✅ Automatic SQL query generation
- ✅ Database schema understanding  
- ✅ Result formatting and visualization
- ✅ Error handling and query optimization

### Research Agent (Web Search)

Ideal for information gathering and research:

```python
from agentdk import ResearchAgent

agent = ResearchAgent(
    llm=llm,
    tools=[web_search_tool]
)

# Web research with source citations
result = agent.query("What are the latest developments in AI agent frameworks?")
```

**Features:**
- ✅ Web search integration
- ✅ Source citation and verification
- ✅ Multi-source information synthesis
- ✅ Fact-checking and validation

### Custom Agents

Build your own specialized agents:

```python
from agentdk import SubAgentInterface

class CustomAgent(SubAgentInterface):
    def _get_default_prompt(self) -> str:
        return "You are a specialized agent for..."
    
    async def _create_agent(self) -> None:
        # Custom agent initialization
        pass

# Use your custom agent
agent = CustomAgent(llm=llm, tools=custom_tools)
```

## 🔧 Configuration

### Environment Setup

Create a `.env` file for your configuration:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Database Configuration (for EDA agents)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

# Logging
LOG_LEVEL=INFO
```

### Database Setup (Optional)

For EDA agents with database access:

```bash
# Using Docker (recommended)
docker run -d \
  --name agentdk-mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=agentdk_test \
  -e MYSQL_USER=agentdk_user \
  -e MYSQL_PASSWORD=agentdk_pass \
  -p 3306:3306 \
  mysql:8.0

# Or use the provided docker-compose
git clone https://github.com/breadpowder/agentdk.git
cd agentdk/examples
docker-compose up -d
```

## 📚 Examples

### Complete Data Analysis Workflow

```python
from agentdk import EDAAgent
from langchain_openai import ChatOpenAI

# Setup
llm = ChatOpenAI(model="gpt-4")
agent = EDAAgent(llm=llm, mcp_config_path="mcp_config.json")

# Multi-step analysis
queries = [
    "What tables are available?",
    "Show me customer demographics",
    "What are the top 10 customers by transaction volume?",
    "Identify any unusual transaction patterns"
]

for query in queries:
    result = agent.query(query)
    print(f"Query: {query}")
    print(f"Result: {result}\n")
```

### Research and Analysis Combination

```python
from agentdk import Agent  # Supervisor agent

# Supervisor automatically routes to appropriate agents
supervisor = Agent(llm=llm)

# This goes to EDA agent (database query)
data_insight = supervisor("What's our customer retention rate?")

# This goes to Research agent (web search)
market_research = supervisor("What are industry benchmarks for customer retention?")

# Combine insights
analysis = supervisor(f"""
Based on our retention rate of {data_insight} and industry benchmarks 
from {market_research}, provide strategic recommendations.
""")
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the coding standards (use `black`, `isort`, `mypy`)
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Examples and Tutorials

Check out the `examples/` directory for:

- **Basic Agent Setup**: Simple agent configuration and usage
- **Database Integration**: EDA agents with SQL database connectivity
- **Multi-Agent Workflows**: Supervisor patterns with multiple specialized agents
- **MCP Server Integration**: Various MCP server configurations
- **Jupyter Notebooks**: Interactive examples and tutorials

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Homepage**: [https://github.com/breadpowder/agentdk](https://github.com/breadpowder/agentdk)
- **Documentation**: Coming soon
- **Bug Reports**: [GitHub Issues](https://github.com/breadpowder/agentdk/issues)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## Support

For questions and support:

1. Check the [examples/](examples/) directory
2. Review the [memory-bank/](memory-bank/) documentation
3. Open an issue on [GitHub](https://github.com/breadpowder/agentdk/issues)
4. Join our community discussions

---

Built with ❤️ for the LangGraph and MCP community. 