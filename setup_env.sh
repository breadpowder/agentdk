#!/bin/bash

# AgentDK Environment Setup Script
# This script creates a conda environment and installs AgentDK in development mode

set -e  # Exit on any error

# Configuration
ENV_NAME="agentdk"
PYTHON_VERSION="3.11"

echo "🚀 Setting up AgentDK development environment..."
echo "================================================"


# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found"
    echo "Please run this script from the AgentDK project root directory"
    exit 1
fi

echo "📦 Creating conda environment: $ENV_NAME"
echo "Python version: $PYTHON_VERSION"

# Initialize conda for this script
eval "$(conda shell.bash hook)"

# Deactivate current environment if we're in the target environment
if [[ "$CONDA_DEFAULT_ENV" == "$ENV_NAME" ]]; then
    echo "🔄 Deactivating current environment: $CONDA_DEFAULT_ENV"
    conda deactivate
fi

# Remove existing environment if it exists
if conda env list | grep -q "^$ENV_NAME "; then
    echo "🗑️  Removing existing environment: $ENV_NAME"
    conda env remove -n $ENV_NAME -y
fi

# Create new conda environment
echo "🔨 Creating new conda environment..."
conda create -n $ENV_NAME python=$PYTHON_VERSION -y

# Activate environment
echo "⚡ Activating environment..."
conda activate $ENV_NAME

# Verify Python version
echo "🐍 Python version: $(python --version)"
echo "📍 Python location: $(which python)"

# Upgrade pip
echo "📈 Upgrading pip..."
python -m pip install --upgrade pip

# Install the package in editable mode
echo "🔧 Installing AgentDK in development mode..."
pip install -e .

# Install additional development dependencies if they exist
if [ -f "requirements-dev.txt" ]; then
    echo "🧪 Installing development dependencies..."
    pip install -r requirements-dev.txt
elif [ -f "dev-requirements.txt" ]; then
    echo "🧪 Installing development dependencies..."
    pip install -r dev-requirements.txt
else
    echo "📝 Installing common development tools..."
    pip install jupyter notebook ipykernel pytest black isort mypy
fi

# Add kernel to Jupyter
echo "📓 Adding conda environment to Jupyter..."
python -m ipykernel install --user --name=$ENV_NAME --display-name="AgentDK ($ENV_NAME)"
pip install langchain-openai

# Verify installation
echo ""
echo "✅ Installation complete!"
echo "========================================"
echo "📋 Environment Summary:"
echo "  - Environment name: $ENV_NAME"
echo "  - Python version: $(python --version)"
echo "  - Installation location: $(pip show agentdk | grep Location | cut -d' ' -f2)"
echo ""
echo "🎯 Next steps:"
echo "  1. Activate the environment: conda activate $ENV_NAME"
echo "  2. Start Jupyter: jupyter notebook"
echo "  3. Run tests: pytest"
echo "  4. Start coding! 🚀"
echo ""
echo "🗂️  Example usage:"
echo "  cd examples"
echo "  python agent.py"
echo "  # or"
echo "  jupyter notebook agentdk_testing_notebook.ipynb"
echo ""

# Test import
echo "🧪 Testing AgentDK import..."
if python -c "import agentdk; print(f'✅ AgentDK version: {agentdk.__version__ if hasattr(agentdk, \"__version__\") else \"dev\"}')" 2>/dev/null; then
    echo "✅ AgentDK imported successfully!"
else
    echo "⚠️  Warning: AgentDK import test failed, but installation may still work"
fi

echo ""
echo "🎉 Setup complete! Happy coding!" 
