#!/bin/bash
set -e

echo "🚀 AgentDK Test Environment Setup"
echo "================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required dependencies
echo "📋 Checking dependencies..."
if ! command_exists git; then
    echo "❌ Git is required but not installed. Please install Git."
    exit 1
fi

if ! command_exists docker; then
    echo "❌ Docker is required but not installed. Please install Docker."
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose is required but not installed. Please install Docker Compose."
    exit 1
fi

echo "✅ All dependencies found"

# 1. Check out mysql_mcp_server from git if it doesn't exist
echo "📥 Setting up MySQL MCP Server..."
if [ ! -d "mysql_mcp_server" ]; then
    echo "   Cloning mysql_mcp_server repository..."
    git clone https://github.com/designcomputer/mysql_mcp_server.git
    echo "✅ MySQL MCP Server cloned successfully"
else
    echo "✅ MySQL MCP Server directory already exists"
    # Update if it's a git repository
    if [ -d "mysql_mcp_server/.git" ]; then
        echo "   Updating mysql_mcp_server repository..."
        cd mysql_mcp_server
        git pull origin main || git pull origin master || echo "   Warning: Could not update repository"
        cd ..
    fi
fi

# 2. Start docker-compose
echo "🐳 Starting Docker services..."
docker-compose down >/dev/null 2>&1 || true  # Stop any existing containers
docker-compose up -d

echo "⏳ Waiting for MySQL to be ready..."
# Wait for MySQL to be healthy
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if docker-compose exec -T mysql mysqladmin ping -u root -pagentdk_password --silent 2>/dev/null; then
        echo "✅ MySQL is ready!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ MySQL failed to start after $max_attempts attempts"
        echo "   Checking MySQL logs:"
        docker-compose logs mysql
        exit 1
    fi
    
    echo "   Attempt $attempt/$max_attempts - MySQL not ready yet..."
    sleep 2
    attempt=$((attempt + 1))
done

# 3. Wait a bit more for the init.sql to complete
echo "⏳ Waiting for database initialization to complete..."
sleep 5

# 4. Verify database setup
echo "🔍 Verifying database setup..."
if docker-compose exec -T mysql mysql -u agentdk_user -pagentdk_user_password agentdk_test -e "SELECT 'Database verified!' as status, COUNT(*) as customer_count FROM customers;" 2>/dev/null; then
    echo "✅ Database setup completed successfully!"
else
    echo "❌ Database verification failed"
    echo "   Checking if tables exist..."
    docker-compose exec -T mysql mysql -u agentdk_user -pagentdk_user_password agentdk_test -e "SHOW TABLES;" 2>/dev/null || {
        echo "   Error: Could not connect to database or tables don't exist"
        echo "   MySQL logs:"
        docker-compose logs mysql | tail -20
        exit 1
    }
fi

# 5. Display connection information
echo ""
# 6. Setup environment configuration
echo "⚙️ Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f "env.sample" ]; then
        cp env.sample .env
        echo "✅ Created .env file from env.sample"
        echo "   You can edit .env to customize your configuration"
    else
        echo "⚠️  Warning: env.sample not found, creating basic .env"
        cat > .env << EOF
# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=agentdk_user
MYSQL_PASSWORD=agentdk_user_password
MYSQL_DATABASE=agentdk_test

# LLM Configuration (add your API keys)
#OPENAI_API_KEY=your_openai_key_here
$ANTHROPIC_API_KEY=your_anthropic_key_here

# Logging
LOG_LEVEL=INFO
EOF
    fi
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup completed successfully!"
echo "================================="
echo "MySQL Connection Details:"
echo "  Host: localhost"
echo "  Port: 3306" 
echo "  Database: agentdk_test"
echo "  Username: agentdk_user"
echo "  Password: agentdk_user_password"
echo ""
echo "Available tables:"
docker-compose exec -T mysql mysql -u agentdk_user -pagentdk_user_password agentdk_test -e "SHOW TABLES;" 2>/dev/null || echo "  Could not list tables"
echo ""
echo "Sample data counts:"
docker-compose exec -T mysql mysql -u agentdk_user -pagentdk_user_password agentdk_test -e "
SELECT 'customers' as table_name, COUNT(*) as count FROM customers
UNION ALL
SELECT 'accounts' as table_name, COUNT(*) as count FROM accounts  
UNION ALL
SELECT 'transactions' as table_name, COUNT(*) as count FROM transactions;" 2>/dev/null || echo "  Could not get data counts"
echo ""
echo "🚀 You can now run the AgentDK examples!"
echo ""
echo "Environment Configuration:"
echo "  ✅ .env file has been created with database connection settings"
echo "  📝 Edit .env to add your LLM API keys (OpenAI, Anthropic, etc.)"
echo ""
echo "Example usage:"
echo "  python agent.py"
echo ""
echo "To stop the services later, run:"
echo "  docker-compose down" 