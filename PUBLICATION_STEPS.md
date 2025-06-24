# AgentDK Publication Steps

## 📋 Quick Steps to Publish AgentDK to PyPI

### Step 1: Cleanup Codebase
```bash
# Review what will be deleted (dry run)
python scripts/cleanup_unused_files.py

# Execute cleanup to remove debug/test files
python scripts/cleanup_unused_files.py --execute
```

### Step 2: Setup PyPI Authentication
Create `~/.pypirc`:
```ini
[distutils]
index-servers = pypi testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN
```

### Step 3: Test on TestPyPI First
```bash
# Build and publish to TestPyPI
python scripts/publish_to_pypi.py --test-pypi --version 0.1.0

# Test installation
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ agentdk
```

### Step 4: Publish to Production PyPI
```bash
# Publish to production PyPI
python scripts/publish_to_pypi.py --production --version 0.1.0

# Verify installation
pip install agentdk
```

### Step 5: Post-Publication
```bash
# Tag the release
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0

# Test the installation
python -c "from agentdk import EDAAgent; print('✅ AgentDK ready!')"
```

## 🎯 What Gets Cleaned Up

**Removed Files:**
- All debug/test files in `examples/`
- Development docs (`memory-bank/`, `CODE_OPTIMIZATION_REPORT.md`, etc.)
- Build artifacts (`dist/`, `.venv/`, `__pycache__/`)
- IDE files (`.cursor/`)

**Kept Files:**
- Core library (`src/agentdk/`)
- Essential examples (`examples/agent.py`, `examples/simple_agent.py`)
- Database setup (`examples/docker-compose.yml`, `examples/sql/`)
- MCP server example (`examples/mysql_mcp_server/`)
- Tests (`tests/`)

## 📦 Final Package Structure

```
agentdk/
├── src/agentdk/           # Core library
├── examples/              # Essential examples only
├── tests/                 # Unit tests
├── README.md              # Updated usage guide
├── LICENSE                # MIT license
└── pyproject.toml         # Package configuration
```

## 🚀 Users Can Install With

```bash
# Basic installation
pip install agentdk

# With LLM providers
pip install agentdk[openai]
pip install agentdk[anthropic]
pip install agentdk[all]
```

## ✅ Success Criteria

- ✅ `pip install agentdk` works
- ✅ `from agentdk import EDAAgent` succeeds
- ✅ Examples run without errors
- ✅ Package size < 10MB
- ✅ Clean, professional codebase

That's it! Your AgentDK package will be ready for the community to use. 