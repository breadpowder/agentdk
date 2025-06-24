# AgentDK Environment Setup Guide

This guide provides automated scripts to set up your AgentDK development environment using conda.

## Quick Start

### Linux/macOS
```bash
./setup_env.sh
```

### Windows
```cmd
setup_env.bat
```

## What the Scripts Do

Both scripts perform the following actions:

1. **Environment Validation**
   - Check if conda is installed and accessible
   - Verify you're in the correct project directory
   - Ensure `pyproject.toml` exists

2. **Environment Management**
   - Remove existing `agentdk` environment (if present)
   - Create fresh conda environment with Python 3.11
   - Activate the new environment

3. **Package Installation**
   - Upgrade pip to latest version
   - Install AgentDK in editable mode (`pip install -e .`)
   - Install development dependencies (if present)
   - Install common development tools (jupyter, pytest, black, isort, mypy)

4. **Jupyter Integration**
   - Add the conda environment as a Jupyter kernel
   - Enable notebook usage with the AgentDK environment

5. **Verification**
   - Test AgentDK import
   - Display environment summary
   - Provide next steps and usage examples

## Prerequisites

### Required
- **Conda**: Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution)
- **Git**: For cloning the repository
- **Internet Connection**: For downloading packages

### Optional
- **API Keys**: For real LLM testing (OpenAI, Anthropic)
- **Docker**: For MySQL database examples

## Detailed Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/breadpowder/agentdk.git
cd agentdk
```

### 2. Run the Setup Script

#### Linux/macOS
```bash
# Make executable (if needed)
chmod +x setup_env.sh

# Run the script
./setup_env.sh
```

#### Windows
```cmd
# Run from Command Prompt or PowerShell
setup_env.bat
```

### 3. Activate the Environment
```bash
conda activate agentdk
```

### 4. Verify Installation
```bash
# Test basic import
python -c "import agentdk; print('AgentDK imported successfully!')"

# Run example
cd examples
python agent.py
```

## Environment Details

### Created Environment
- **Name**: `agentdk`
- **Python Version**: 3.11
- **Installation Type**: Editable (`pip install -e .`)

### Installed Packages
- **Core Dependencies**: From `pyproject.toml`
  - `langchain_core>=0.3.0,<0.4.0`
  - `langchain-mcp-adapters>=0.1.7,<0.2.0`
  - `langgraph>=0.2.20,<0.3.0`
  - `pydantic>=2.11.5,<3.0.0`
  - And more...

- **Development Tools**:
  - `jupyter` - For running notebooks
  - `pytest` - For running tests
  - `black` - Code formatting
  - `isort` - Import sorting
  - `mypy` - Type checking

### Jupyter Kernel
- **Kernel Name**: `agentdk`
- **Display Name**: "AgentDK (agentdk)"
- **Usage**: Select this kernel when running Jupyter notebooks

## Troubleshooting

### Common Issues

#### 1. Conda Not Found
```
❌ Error: conda is not installed or not in PATH
```
**Solution**: Install conda and ensure it's in your PATH:
- Download [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- Follow installation instructions
- Restart your terminal

#### 2. Wrong Directory
```
❌ Error: pyproject.toml not found
```
**Solution**: Navigate to the AgentDK project root:
```bash
cd /path/to/agentdk
./setup_env.sh
```

#### 3. Permission Denied (Linux/macOS)
```
bash: ./setup_env.sh: Permission denied
```
**Solution**: Make the script executable:
```bash
chmod +x setup_env.sh
./setup_env.sh
```

#### 4. Environment Creation Failed
**Solution**: Try manual cleanup:
```bash
conda env remove -n agentdk -y
conda clean --all
./setup_env.sh
```

#### 5. Package Installation Failed
**Solution**: Check internet connection and try:
```bash
conda activate agentdk
pip install --upgrade pip
pip install -e .
```

### Manual Installation

If the automated scripts fail, you can set up manually:

```bash
# Create environment
conda create -n agentdk python=3.11 -y
conda activate agentdk

# Upgrade pip
python -m pip install --upgrade pip

# Install AgentDK
pip install -e .

# Install development tools
pip install jupyter notebook ipykernel pytest black isort mypy

# Add Jupyter kernel
python -m ipykernel install --user --name=agentdk --display-name="AgentDK (agentdk)"
```

## Next Steps After Setup

### 1. Test Basic Functionality
```bash
conda activate agentdk
cd examples
python agent.py
```

### 2. Run Jupyter Notebook
```bash
conda activate agentdk
jupyter notebook examples/agentdk_testing_notebook.ipynb
```

### 3. Set Up Database (Optional)
```bash
cd examples
docker-compose up -d
```

### 4. Configure API Keys (Optional)
```bash
# Add to your .bashrc, .zshrc, or .env file
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### 5. Run Tests
```bash
conda activate agentdk
pytest
```

## Development Workflow

1. **Activate Environment**: `conda activate agentdk`
2. **Make Changes**: Edit code in `src/agentdk/`
3. **Test Changes**: Changes are automatically available (editable install)
4. **Run Tests**: `pytest`
5. **Format Code**: `black src/` and `isort src/`
6. **Type Check**: `mypy src/`

## Support

If you encounter issues:

1. Check this troubleshooting guide
2. Review the setup script output for specific error messages
3. Open an issue on [GitHub](https://github.com/breadpowder/agentdk/issues)
4. Include your OS, Python version, and error messages

## Script Customization

### Environment Name
To use a different environment name, edit the scripts:

**Linux/macOS (`setup_env.sh`)**:
```bash
ENV_NAME="your-custom-name"
```

**Windows (`setup_env.bat`)**:
```batch
set ENV_NAME=your-custom-name
```

### Python Version
To use a different Python version:

**Linux/macOS (`setup_env.sh`)**:
```bash
PYTHON_VERSION="3.12"
```

**Windows (`setup_env.bat`)**:
```batch
set PYTHON_VERSION=3.12
```

---

🎉 **Happy coding with AgentDK!** 🚀 