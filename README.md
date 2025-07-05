# AgentDK - Agent Development Kit for LangGraph + MCP Integration

A powerful Python framework for building intelligent agents using LangGraph and Model Context Protocol (MCP) integration. AgentDK simplifies the creation of multi-agent systems with MCP support and runs seamlessly in Jupyter/IPython environments.

## 🚀 Key Features

- **🤖 Multi-Agent Architecture**: Build sophisticated agent systems using LangGraph supervisor patterns
- **🔌 MCP Integration**: Seamless integration with Model Context Protocol servers for standardized tool access
- **🧠 Memory System**: Integrated memory capabilities for conversation continuity and user preferences
- **🔄 Async Support**: Full async/await support for scalable agent operations with Jupyter/IPython compatibility
- **🎯 Production Ready**: Comprehensive testing, logging, and error handling

## 📦 Installation

```bash
# Install from PyPI
pip install agentdk[all] 

```

## 🏁 Quick Start

### Basic EDA Agent Usage

```python
from agentdk.agent.factory import create_agent
from agentdk.agent.agent_interface import AgentConfig

# Set up configuration
config = AgentConfig(mcp_config_path="examples/subagent/mcp_config.json")

# Create EDA agent with MCP integration
eda_agent = create_agent("eda", config=config, llm=llm)

# Query your database
result = eda_agent.query("How many customers do we have?")
print(result)

# Complex analysis
result = eda_agent.query("Show me the top 5 customers by total account balance")
print(result)
```

### Multi-Agent Supervisor Pattern

```python
from agentdk.agent.base_app import BaseMemoryApp

class App(BaseMemoryApp):
    """Multi-agent app with supervisor workflow."""
    
    def __init__(self, model, memory=True, user_id="default"):
        super().__init__(model=model, memory=memory, user_id=user_id)
        self.app = self.create_workflow(model)
    
    def create_workflow(self, model):
        """Create supervisor with EDA and research agents."""
        from examples.subagent.eda_agent import create_eda_agent
        from examples.subagent.research_agent import create_research_agent
        
        # Create specialized agents
        eda_agent = create_eda_agent(model, "examples/subagent/mcp_config.json")
        research_agent = create_research_agent(model)
        
        # Create supervisor workflow
        return create_supervisor_workflow([eda_agent, research_agent], model)

# Usage
app = App(model=llm, memory=True, user_id="analyst_001")
result = app("Analyze customer transaction patterns and provide insights")
```

### Jupyter Notebook Integration

```python
# For Jupyter environments
from agentdk.core.logging_config import ensure_nest_asyncio
ensure_nest_asyncio()  # Enables async support in notebooks

# Run interactive analysis
app = App(model=llm, memory=True)
result = app("What are the latest customer trends?")
```

## 🖥️ CLI Usage

AgentDK provides a command-line interface for interactive agent deployment and testing.

### Installation & Setup

The CLI is automatically available after installing AgentDK:

```bash
# Install with CLI support (includes LLM dependencies)
pip install agentdk[cli]

# Set up environment variables for LLM access
export OPENAI_API_KEY="your-openai-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Basic CLI Commands

```bash
# Run an agent interactively
agentdk run examples/subagent/eda_agent.py

# Resume previous session
agentdk run examples/subagent/eda_agent.py --resume

# Specify LLM provider
agentdk run examples/subagent/research_agent.py --llm openai

# Get help
agentdk --help
agentdk run --help
```

### Interactive Session Example

```bash
$ agentdk run examples/subagent/eda_agent.py
Loading agent from examples/subagent/eda_agent.py...
✅ Using OpenAI gpt-4o-mini
Agent 'eda_agent' ready. Type 'exit' to quit, 'help' for commands.

[user]: How many tables are available?
[eda_agent]: I can help you analyze your database. Let me check the available tables...

[user]: help
Available commands:
  help    - Show this help message
  clear   - Clear the screen
  exit    - Exit the session (also: quit, q, Ctrl+D)

[user]: exit
Session ended. Conversation saved for eda_agent.
Session saved with 2 interactions.
Resume with: agentdk run <agent_path> --resume
```

### Session Management

- **Automatic Saving**: All conversations are automatically saved
- **Resume Sessions**: Use `--resume` to continue previous conversations
- **Session Storage**: Sessions stored in `~/.agentdk/sessions/`
- **Cross-Platform**: Works on Linux, macOS, and Windows

### Supported Agent Patterns

The CLI automatically detects and loads agents using these patterns:

```python
# Pattern 1: Factory function
def create_my_agent(llm=None, **kwargs):
    return Agent().with_llm(llm).build()

# Pattern 2: Direct agent instance
root_agent = Agent().with_llm(llm).build()
```

### 🔧Set up MCP Servers
MCP (Model Context Protocol) servers provide standardized tool access. Here's how to configure them:

#### MySQL MCP Server Example

Create a `mcp_config.json` file with your MCP server configuration. **Note: Relative paths in configuration are resolved relative to the config file's location.**

```json
{
  "mysql": {
    "command": "uv",
    "args": [
      "--directory",
      "../mysql_mcp_server",
      "run",
      "mysql_mcp_server"
    ],
    "env": {
      "MYSQL_HOST": "localhost",
      "MYSQL_PORT": "3306",
      "MYSQL_USER": "agentdk_user",
      "MYSQL_PASSWORD": "agentdk_user_password",
      "MYSQL_DATABASE": "agentdk_test"
    },
    "transport": "stdio"
  }
}
```

The relative path `../mysql_mcp_server` is automatically resolved to the absolute path based on the config file's location, making your configuration portable across different systems.

## 📚 Examples and Use Cases

Explore the [examples/](examples/) directory for comprehensive demonstrations:

### Core Examples
- **[agent_app.py](examples/agent_app.py)**: Complete multi-agent supervisor app with memory integration
- **[agentdk_testing_notebook.ipynb](examples/agentdk_testing_notebook.ipynb)**: Interactive Jupyter notebook with real-time examples
- **[integration_test.py](examples/integration_test.py)**: Full end-to-end testing and validation

### Specialized Agents
- **[subagent/eda_agent.py](examples/subagent/eda_agent.py)**: Database analysis agent with MySQL MCP integration
- **[subagent/research_agent.py](examples/subagent/research_agent.py)**: Web research agent with custom tools
- **[subagent/mcp_config.json](examples/subagent/mcp_config.json)**: MCP server configuration template

### Infrastructure
- **[setup.sh](examples/setup.sh)**: Automated environment setup script
- **[docker-compose.yml](examples/docker-compose.yml)**: MySQL database with sample data
- **[mysql_mcp_server/](examples/mysql_mcp_server/)**: Complete MCP server implementation


## 🚀 Getting Started

### 1. Quick Setup

```bash
git clone https://github.com/breadpowder/agentdk.git
cd agentdk/examples
./setup.sh  # Automated setup with MySQL and MCP servers
```

### 2. Configure Environment

```bash
# Copy template and add your API keys
cp .env.example .env
# Edit .env with your OpenAI/Anthropic API keys
```

### 3. Run Examples

```bash
# Basic agent usage
python examples/agent_app.py

# Interactive notebook
jupyter lab examples/agentdk_testing_notebook.ipynb

# Full integration test
python examples/integration_test.py
```

### UV Environment Setup (Alternative)

If you prefer using `uv` for faster package management:

```bash
# 1. Install Python 3.11 (if not already available)
uv python install 3.11

# 2. Create virtual environment with Python 3.11
uv venv --python 3.11

# 3. Activate environment and install project with all dependencies
source .venv/bin/activate && uv pip install -e .[all]

# 4. Install Jupyter and ipykernel
uv pip install jupyter ipykernel

# 5. Register the environment as a Jupyter kernel
python -m ipykernel install --user --name agentdk --display-name "AgentDK (Python 3.11)"

# 6. Verify kernel installation
jupyter kernelspec list

# 7. Launch Jupyter Lab
jupyter lab
```
Then run [agentdk_testing_notebook.ipynb](examples/agentdk_testing_notebook.ipynb)

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
2. Review the documentation in the repository
3. Open an issue on [GitHub](https://github.com/breadpowder/agentdk/issues)
4. Join our community discussions

---

Built with ❤️ for the LangGraph and MCP community. 