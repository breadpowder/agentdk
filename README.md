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

### Building Custom Multi-Agent Workflows

See [examples/](examples/) directory for complete implementation details.

### Building Multi-Agent Apps with Memory

```python
from agentdk.memory import MemoryAwareAgent
from subagent.eda_agent import EDAAgent
from subagent.research_agent import ResearchAgent

class App(MemoryAwareAgent):
    """Enhanced App with memory integration."""

    def __init__(self, model, memory=True, user_id="default", memory_config=None):
        self.model = model
        super().__init__(memory=memory, user_id=user_id, memory_config=memory_config)
        self.app = self.create_workflow(model)

    def create_workflow(self, model):
        """Create a supervisor workflow with research and EDA agents."""
        
        def web_search(query: str) -> str:
            """Search the web for information."""
            # Your web search implementation
            pass
        
        try:
            from langgraph_supervisor import create_supervisor
            
            # Create specialized agents
            eda_agent = EDAAgent(
                llm=model,
                mcp_config_path="subagent/mcp_config.json",
                name="eda_agent"
            )
            
            research_agent = ResearchAgent(
                llm=model,
                tools=[web_search],
                name="research_expert"
            )
            
            # Create supervisor workflow
            workflow = create_supervisor(
                [research_agent, eda_agent],
                model=model,
                prompt=self._create_supervisor_prompt()
            )
            
            return workflow.compile()
            
        except ImportError as e:
            print(f"Missing dependency: {e}")
            raise

# Usage with memory integration
app = App(
    model=llm,
    memory=True,
    user_id="analyst_001"
)

# Complex multi-step analysis with memory continuity
result = app("""
Analyze customer transaction data
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