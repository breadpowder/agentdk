# AgentDK - Agent Development Kit for LangGraph + MCP Integration

A powerful Python framework for building intelligent agents using LangGraph and Model Context Protocol (MCP) integration. AgentDK simplifies the creation of multi-agent systems with MCP support and runs seamlessly in Jupyter/IPython environments.

## 🚀 Key Features

- **🤖 Multi-Agent Architecture**: Build sophisticated agent systems using LangGraph supervisor patterns
- **🔌 MCP Integration**: Seamless integration with Model Context Protocol servers for standardized tool access
- **🔄 Async Support**: Full async/await support for scalable agent operations with Jupyter/IPython compatibility
- **🎯 Production Ready**: Comprehensive testing, logging, and error handling

## 📦 Installation

```bash
# Install from PyPI
pip install agentdk[all] 

```

## 🏁 Quick Start

### Building Custom Multi-Agent Workflows

See [examples/](examples/) directory for complete implementation details.

### Define Custom Agents
```python
from agentdk import SubAgentInterface

class EDAAgent(SubAgentInterface):
    def _get_default_prompt(self) -> str:
        return "You are a specialized agent for exploratory data analysis..."
    
    async def _create_agent(self) -> None:
        # Custom agent initialization
        pass

class ResearchAgent(SubAgentInterface):
    def _get_default_prompt(self) -> str:
        return "You are a specialized agent for research and analysis..."
    
    async def _create_agent(self) -> None:
        # Custom agent initialization
        pass
```

```python
from agentdk.prompts import get_supervisor_prompt

# Create specialized agents
eda_agent = EDAAgent(
    llm=llm,
    mcp_config_path="mcp_config.json", ## see below for MCP conf set up
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

**Key Features:**
- **✅ Relative Path Support**: Use `../mysql_mcp_server` instead of hardcoded absolute paths
- **✅ Portable Configuration**: Works regardless of where your project is installed
- **✅ Environment Variables**: Configure database connection details via env vars
- **✅ UV Integration**: Uses `uv` for fast package management and execution

The relative path `../mysql_mcp_server` is automatically resolved to the absolute path based on the config file's location, making your configuration portable across different systems.

## Examples and Tutorials
Check out the [examples/](examples/) directory for:
- **Basic Agent Setup**: Simple agent configuration and usage
- **Database Integration**: EDA agents with SQL database connectivity  
- **Multi-Agent Workflows**: Supervisor patterns with multiple specialized agents
- **MCP Server Integration**: Various MCP server configurations
- **Jupyter Notebooks**: Interactive examples and tutorials


## 🔧 Running Examples
### Environment Setup

```bash
git clone https://github.com/breadpowder/agentdk.git
cd agentdk/examples
sh setup.sh
```

The setup script automatically creates your `.env` file from `env.sample`. Configure your environment variables:
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