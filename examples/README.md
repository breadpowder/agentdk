# AgentDK Examples

This directory contains examples demonstrating how to use the AgentDK framework with various sub-agents and MCP servers.

## Quick Setup

### Automated Setup (Recommended)

For the fastest setup, use our automated script:

```bash
# Navigate to the examples directory
cd examples

# Run the automated setup script
./setup.sh
```

This script will:
- Clone the MySQL MCP Server repository if it doesn't exist
- Start the MySQL Docker container with sample data
- Wait for database initialization to complete
- Verify the setup and display connection details

### Manual Setup

If you prefer to set up manually:

#### 1. MySQL MCP Server Setup

Clone the MySQL MCP Server if not already present:

```bash
# Clone MySQL MCP Server (if not exists)
git clone https://github.com/designcomputer/mysql_mcp_server.git
```

#### 2. MySQL Docker Setup

The examples use a MySQL database with sample data. To set up the database:

```bash
# Navigate to the examples directory
cd examples

# Start MySQL container with sample data
docker-compose up -d

# Wait for MySQL to be ready (check logs)
docker-compose logs mysql

# Verify the database is accessible
docker exec agentdk_mysql mysql -u agentdk_user -pagentdk_user_password agentdk_test -e "SELECT COUNT(*) FROM customers;"
```

#### 3. Install Dependencies

Make sure you have the required Python dependencies:

```bash
# Install AgentDK dependencies
pip install langgraph langchain-mcp-adapters

# Install MySQL MCP server
pip install mysql-mcp-server

# Or using uvx (recommended for MCP servers)
uvx install mysql-mcp-server
```

#### 4. Environment Configuration

AgentDK supports both environment variables and `.env` file configuration for flexible deployment.

##### Option A: Using .env File (Recommended)

1. Copy the sample environment file:
   ```bash
   cp env.sample .env
   ```

2. Edit `.env` file with your configuration:
   ```bash
   # MySQL Database Configuration
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=agentdk_user
   MYSQL_PASSWORD=agentdk_user_password
   MYSQL_DATABASE=agentdk_test
   
   # AI Model Configuration (optional)
   # OPENAI_API_KEY=your_openai_api_key_here
   # ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Usage Examples

### Basic EDA Agent Usage

```python
from subagent.eda_agent import EDAAgent

# Create EDA agent (replace with your actual LLM)
# from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4")

eda_agent = EDAAgent(
    llm=llm,  # Your LLM instance
    mcp_config_path="subagent/mcp_config.json"
)

# Ask questions about the data
result = eda_agent.query("How many customers do we have?")
print(result)

result = eda_agent.query("What's the total balance across all accounts?")
print(result)

result = eda_agent.query("Show me the top 5 customers by total account balance")
print(result)
```

### Supervisor Pattern with Multiple Agents

```python
from agent import create_workflow, sync_example, async_example
import asyncio

# Using the supervisor workflow (async)
async def main():
    workflow = await create_workflow(llm)
    result = await workflow.ainvoke({
        "query": "What insights can you provide about our customer transactions?"
    })
    print(result)

# Run async example
asyncio.run(main())

# Or use the sync example for Jupyter notebooks
result = sync_example(llm, "Analyze the customer demographics and account types")
print(result)
```

### Running the Examples

```bash
# Run the main example
python agent.py

# Or in Jupyter notebook
jupyter notebook
# Then run the examples interactively
```

## Sample Database Schema

The MySQL database contains the following tables:

### Customers Table
- `customer_id` (Primary Key)
- `first_name`, `last_name`
- `email`, `phone`
- `date_of_birth`
- `customer_status` (active, inactive, suspended)
- `credit_score`, `annual_income`

### Accounts Table
- `account_id` (Primary Key)
- `customer_id` (Foreign Key)
- `account_number`, `account_type`
- `balance`, `currency`
- `opened_date`, `status`
- `interest_rate`

### Transactions Table
- `transaction_id` (Primary Key)
- `account_id` (Foreign Key)
- `transaction_type`, `amount`
- `transaction_date`, `description`
- `merchant_name`, `category`
- `status`

### Views
- `customer_account_summary` - Aggregated customer account information
- `monthly_transaction_summary` - Transaction summaries by month and type

## Sample Queries

Here are some example questions you can ask the EDA agent:

1. **Customer Analysis:**
   - "How many active customers do we have?"
   - "What's the average credit score of our customers?"
   - "Show me customers with the highest annual income"

2. **Account Analysis:**
   - "What types of accounts do we offer and how many of each?"
   - "What's the total balance across all accounts?"
   - "Which customers have investment accounts?"

3. **Transaction Analysis:**
   - "What are the most common transaction types?"
   - "Show me recent transactions for account CHK-1001"
   - "What's the average transaction amount by category?"

4. **Complex Analysis:**
   - "Identify customers who haven't made any transactions recently"
   - "Compare spending patterns between different account types"
   - "Find accounts with unusual transaction patterns"

## Troubleshooting

### Quick Fix - Use Automated Setup

If you encounter any setup issues, try running the automated setup script:

```bash
./test_setup.sh
```

This script includes comprehensive error checking and will provide detailed feedback about any issues.

### MySQL Connection Issues

1. **Check if MySQL container is running:**
   ```bash
   docker ps | grep agentdk_mysql
   ```

2. **Check MySQL logs:**
   ```bash
   docker-compose logs mysql
   ```

3. **Test connection manually:**
   ```bash
   docker exec agentdk_mysql mysql -u agentdk_user -pagentdk_user_password agentdk_test -e "SHOW TABLES;"
   ```

### MCP Server Issues

1. **Check if mysql-mcp-server is installed:**
   ```bash
   uvx list | grep mysql-mcp-server
   ```

2. **Test MCP server manually:**
   ```bash
   uvx mysql-mcp-server
   ```

### Agent Issues

1. **Check AgentDK installation:**
   ```bash
   python -c "import src.agentdk; print('AgentDK imported successfully')"
   ```

2. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## Stopping the Services

When you're done testing:

```bash
# Stop MySQL container
docker-compose down

# Remove volumes (optional - this will delete the data)
docker-compose down -v
``` 