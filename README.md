# AgentDK - Agent Development Kit

A Python framework for building intelligent agents with LangGraph + MCP integration. Create data analysis agents, multi-agent workflows, and persistent CLI interactions.

## 🚀 Key Features

- **🤖 Agent Workflows**: Individual agents and multi-agent supervisor patterns  
- **🔌 MCP Integration**: Model Context Protocol servers for standardized tool access
- **🧠 Memory & Sessions**: Conversation continuity and user preferences
- **🖥️ CLI Interface**: Interactive sessions with `agentdk run`

## 📦 Installation

Choose your installation method based on your needs:

### Option 1: PyPI Install (Library Usage)

**Best for**: Using AgentDK as a library in your projects, creating custom agents

```bash
pip install agentdk[all]
```

This installs AgentDK with all dependencies and includes working examples.

### Option 2: GitHub Clone (Development & Examples)

**Best for**: Exploring examples, contributing, or development with database setup

```bash
# Clone repository
git clone https://github.com/breadpowder/agentdk.git
cd agentdk

# Create UV environment (recommended)
uv venv --python 3.11
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install with all dependencies
uv sync --extra all

# Set up examples environment with database
cd examples
./setup.sh  # Sets up MySQL database with Docker
```

## 🏁 Quick Start

### After PyPI Install

Set your API key and try a simple agent:

```bash
# Set your API key
export OPENAI_API_KEY="your-key"
# or export ANTHROPIC_API_KEY="your-key"

# Try the included EDA agent example
agentdk run -m agentdk.examples.subagent.eda_agent

# Or run the multi-agent supervisor
agentdk run -m agentdk.examples.agent_app
```

### After GitHub Clone

```bash
# Set your API key
export OPENAI_API_KEY="your-key"

# Run examples from the examples directory
cd examples
agentdk run subagent/eda_agent.py
agentdk run agent_app.py

# Interactive sessions with memory
agentdk run subagent/eda_agent.py --resume
```

### Interactive Session Example

```bash
$ agentdk run -m agentdk.examples.subagent.eda_agent
✅ Using OpenAI gpt-4o-mini
Agent ready. Type 'exit' to quit.

[user]: How many customers are in the database?
[eda_agent]: Let me check the customer count...

[user]: exit
Session saved. Resume with: agentdk run <path> --resume
```

## 🛠️ How to Define Your Own Agents

### 1. Simple Agent (Database Analysis)

Create a basic agent that connects to a database via MCP:

```python
from agentdk.builder.agent_builder import buildAgent

def create_my_agent(llm, mcp_config_path=None, **kwargs):
    """Create a database analysis agent."""
    return buildAgent(
        agent_class="SubAgentWithMCP",
        llm=llm,
        mcp_config_path=mcp_config_path or "mcp_config.json",
        name="my_agent",
        prompt="You are a helpful database analyst. Help users explore and analyze data.",
        **kwargs
    )
```

#### MCP Configuration Setup

Create `mcp_config.json` for database access:

```json
{
  "mysql": {
    "command": "uv",
    "args": ["--directory", "../mysql_mcp_server", "run", "mysql_mcp_server"],
    "env": {
      "MYSQL_HOST": "localhost",
      "MYSQL_PORT": "3306",
      "MYSQL_USER": "your_user",
      "MYSQL_PASSWORD": "your_password",  
      "MYSQL_DATABASE": "your_database"
    }
  }
}
```

**Path Resolution Rules:**
- **Relative paths** (like `"../mysql_mcp_server"`) are resolved relative to the config file location
- **Absolute paths** work from any location
- AgentDK searches for configs in this order:
  1. Explicit path provided to agent
  2. Same directory as your agent file
  3. Current working directory
  4. Parent directory
  5. Examples directory (if exists)

### 2. Multi-Agent Supervisor Pattern

Combine multiple specialized agents:

```python
from agentdk.agent.base_app import RootAgent
from agentdk.agent.app_utils import create_supervisor_workflow

class MyApp(RootAgent):
    """Multi-agent application with supervisor workflow."""
    
    def create_workflow(self, llm):
        # Create specialized agents
        data_agent = create_my_agent(llm, "config/mcp_config.json")
        research_agent = create_research_agent(llm)
        
        # Create supervisor that routes between agents
        return create_supervisor_workflow([data_agent, research_agent], llm)

# Usage
app = MyApp(llm=your_llm, memory=True)
result = app("Analyze our customer data and research market trends")
```

### 3. Agent Without MCP (Custom Tools)

For agents with custom Python functions:

```python
from agentdk.agent.factory import create_agent

def my_custom_tool(query: str) -> str:
    """Custom tool implementation."""
    return f"Processed: {query}"

# Create agent with custom tools
agent = create_agent(
    agent_type="tools",
    llm=your_llm,
    tools=[my_custom_tool],
    name="custom_agent",
    prompt="You are a helpful assistant with custom tools."
)

result = agent.query("Help me with something")
```

### 4. CLI Integration

Make your agent runnable with `agentdk run`:

```python
# my_agent.py
from agentdk.core.logging_config import ensure_nest_asyncio

# Enable async support
ensure_nest_asyncio()

def create_my_agent(llm=None, **kwargs):
    """Factory function for CLI loading."""
    return buildAgent(
        agent_class="SubAgentWithMCP",
        llm=llm,
        mcp_config_path="config/mcp_config.json",
        name="my_agent",
        prompt="You are my custom agent.",
        **kwargs
    )

# CLI will auto-detect this function
```

Then run: `agentdk run my_agent.py`

## 🔧 MCP Configuration Guide

### Config File Locations

AgentDK searches for `mcp_config.json` in this priority order:

1. **Explicit path**: `create_agent(mcp_config_path="/absolute/path/to/config.json")`
2. **Agent directory**: Same folder as your agent Python file
3. **Working directory**: Where you run the command from
4. **Parent directory**: One level up from working directory
5. **Examples directory**: If `examples/` folder exists

### Path Types

**Relative Paths (Recommended):**
```json
{
  "mysql": {
    "command": "uv",
    "args": ["--directory", "../mysql_mcp_server", "run", "mysql_mcp_server"]
  }
}
```
- Resolved relative to config file location
- Portable across different systems
- Works when moving project directories

**Absolute Paths:**
```json
{
  "mysql": {
    "command": "/usr/local/bin/mysql_mcp_server",
    "args": ["--host", "localhost"]
  }
}
```
- Fixed system paths
- Not portable but explicit

### Environment Variables

Add environment variables to your MCP server config:

```json
{
  "mysql": {
    "command": "mysql_mcp_server",
    "args": ["--config", "mysql.conf"],
    "env": {
      "MYSQL_HOST": "localhost",
      "MYSQL_PORT": "3306",
      "MYSQL_USER": "agent_user",
      "MYSQL_PASSWORD": "secure_password",
      "MYSQL_DATABASE": "production_db"
    }
  }
}
```

## 📁 Examples Directory

**Note**: Examples are included in PyPI installs and available via `-m agentdk.examples`

| File | Description | Run Command |
|------|-------------|-------------|
| `agent_app.py` | Multi-agent supervisor with EDA + research | `agentdk run -m agentdk.examples.agent_app` |
| `subagent/eda_agent.py` | Database analysis agent with MySQL MCP | `agentdk run -m agentdk.examples.subagent.eda_agent` |
| `subagent/research_agent.py` | Web research agent | `agentdk run -m agentdk.examples.subagent.research_agent` |

**For GitHub installations:**
| File | Description | Run Command |
|------|-------------|-------------|
| `setup.sh` | Environment setup with database | `./setup.sh` |
| `agentdk_testing_notebook.ipynb` | Jupyter notebook examples | `jupyter lab` |

## 🔧 Troubleshooting

### Common Issues

**"No valid MCP configuration found"**
```bash
# Check your current directory and config location
ls -la mcp_config.json

# Use absolute path
agentdk run --mcp-config /full/path/to/mcp_config.json my_agent.py

# Or ensure you're in the right directory
cd /path/to/your/project
agentdk run my_agent.py
```

**"MySQL connection failed"**
```bash
# For GitHub installations, ensure database is running
cd examples
./setup.sh
docker ps  # Should show mysql container

# Check your environment variables
echo $MYSQL_HOST $MYSQL_USER $MYSQL_PASSWORD
```

**"agentdk command not found"**
```bash
# Reinstall with CLI dependencies
pip install agentdk[all]
# or for UV
uv sync --extra all
```

**"Examples not found after pip install"**
```bash
# Use module syntax for PyPI installs
agentdk run -m agentdk.examples.subagent.eda_agent

# Or clone GitHub repo for development
git clone https://github.com/breadpowder/agentdk.git
```

### Environment Requirements
- Python 3.11+
- Docker (for database examples)
- OpenAI or Anthropic API key

## 🚀 Advanced Usage

### Memory and Sessions

```python
# Enable memory for conversation continuity
app = MyApp(llm=your_llm, memory=True, user_id="analyst_001")

# Sessions persist across CLI runs
agentdk run my_agent.py --resume --user-id analyst_001
```

### Custom Memory Configuration

```python
memory_config = {
    "provider": "mem0",
    "working_memory_limit": 10,
    "episodic_memory_limit": 100
}

app = MyApp(llm=your_llm, memory=True, memory_config=memory_config)
```

### Jupyter Integration

```python
from agentdk.core.logging_config import ensure_nest_asyncio

# Enable async support in notebooks
ensure_nest_asyncio()

# Use agents in Jupyter
agent = create_my_agent(llm)
result = agent.query("What data do we have?")
```

## License
MIT License - see [LICENSE](LICENSE) file for details.

## Links
- **Homepage**: [https://github.com/breadpowder/agentdk](https://github.com/breadpowder/agentdk)
- **Bug Reports**: [GitHub Issues](https://github.com/breadpowder/agentdk/issues)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

Built with ❤️ for the LangGraph and MCP community.