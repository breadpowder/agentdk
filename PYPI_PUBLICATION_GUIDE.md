# AgentDK PyPI Publication Guide

This guide walks you through the process of cleaning up the codebase and publishing AgentDK to PyPI.

## Prerequisites

1. **PyPI Account**: Create accounts on both [TestPyPI](https://test.pypi.org/) and [PyPI](https://pypi.org/)
2. **API Tokens**: Generate API tokens for both TestPyPI and PyPI
3. **uv installed**: Ensure you have `uv` package manager installed
4. **Git repository**: Clean git state with all changes committed

## Step 1: Cleanup Unused Files

First, clean up debug files, tests, and development artifacts:

```bash
# Review what will be deleted (dry run)
python scripts/cleanup_unused_files.py

# Execute the cleanup
python scripts/cleanup_unused_files.py --execute
```

**Files that will be removed:**
- All debug and test files in `examples/`
- Development documentation (`memory-bank/`, `CODE_OPTIMIZATION_REPORT.md`, etc.)
- Build artifacts and cache directories
- IDE-specific files (`.cursor/`)

**Files that will be kept:**
- Core library code in `src/agentdk/`
- Essential examples (`examples/agent.py`, `examples/simple_agent.py`)
- Database setup (`examples/docker-compose.yml`, `examples/sql/`)
- MCP server example (`examples/mysql_mcp_server/`)
- Unit tests in `tests/` (for development)

## Step 2: Setup PyPI Authentication

### Configure API Tokens

Create `~/.pypirc` file:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

### Alternative: Environment Variables

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_TOKEN_HERE
```

## Step 3: Pre-Publication Checklist

### Verify Package Configuration

```bash
# Check pyproject.toml is valid
python scripts/publish_to_pypi.py --version 0.1.0

# Run tests
uv run pytest tests/ -v

# Check package can be built
uv build
```

### Update Version (if needed)

```bash
# Update version in pyproject.toml
python scripts/publish_to_pypi.py --version 0.1.1
```

## Step 4: Test Publication (Recommended)

Always test on TestPyPI first:

```bash
# Publish to TestPyPI
python scripts/publish_to_pypi.py --test-pypi --version 0.1.0

# Or manually with uv
uv build
uv publish --repository-url https://test.pypi.org/legacy/
```

### Verify TestPyPI Installation

```bash
# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ agentdk

# Test basic import
python -c "import agentdk; print('✅ AgentDK imported successfully')"
```

## Step 5: Production Publication

Once TestPyPI works correctly:

```bash
# Publish to production PyPI
python scripts/publish_to_pypi.py --production --version 0.1.0

# Or manually with uv
uv publish
```

## Step 6: Verify Production Installation

```bash
# Install from PyPI
pip install agentdk

# Test installation
python -c "from agentdk import EDAAgent; print('✅ AgentDK ready for use')"
```

## Publication Script Usage

The `scripts/publish_to_pypi.py` script supports various options:

```bash
# Basic usage - publishes to TestPyPI
python scripts/publish_to_pypi.py

# Specify version
python scripts/publish_to_pypi.py --version 0.1.1

# Publish to production PyPI
python scripts/publish_to_pypi.py --production --version 0.1.0

# Skip tests (not recommended)
python scripts/publish_to_pypi.py --skip-tests

# Use existing build
python scripts/publish_to_pypi.py --skip-build
```

## Manual Publication Steps

If you prefer manual control:

### 1. Build Package
```bash
# Clean previous builds
rm -rf dist/

# Build with uv
uv build
```

### 2. Check Package
```bash
# List built files
ls -la dist/

# Check package contents
tar -tzf dist/agentdk-*.tar.gz
```

### 3. Upload to TestPyPI
```bash
uv publish --repository-url https://test.pypi.org/legacy/
```

### 4. Upload to PyPI
```bash
uv publish
```

## Post-Publication Tasks

### 1. Tag Release
```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

### 2. Update Documentation
- Update README.md with installation instructions
- Create release notes
- Update examples to use published package

### 3. Announce Release
- GitHub release
- Community announcements
- Documentation updates

## Troubleshooting

### Common Issues

**Build Failures:**
```bash
# Check dependencies
uv sync

# Validate pyproject.toml
python -c "import toml; toml.load('pyproject.toml')"
```

**Upload Failures:**
```bash
# Check authentication
cat ~/.pypirc

# Verify network connection
curl -I https://pypi.org/
```

**Import Errors:**
```bash
# Check package structure
python -c "import sys; print(sys.path)"
pip show agentdk
```

### Version Conflicts

If version already exists on PyPI:
1. Increment version number
2. Update pyproject.toml
3. Rebuild and republish

```bash
python scripts/publish_to_pypi.py --version 0.1.1
```

## Security Best Practices

1. **Never commit API tokens** to version control
2. **Use environment variables** for sensitive data
3. **Rotate tokens regularly**
4. **Use 2FA** on PyPI accounts
5. **Review package contents** before publishing

## Maintenance Workflow

For future releases:

1. **Development Phase**:
   - Work in feature branches
   - Add tests for new features
   - Update documentation

2. **Pre-Release**:
   - Run cleanup script
   - Update version number
   - Test on TestPyPI

3. **Release**:
   - Publish to PyPI
   - Tag release in Git
   - Update documentation

4. **Post-Release**:
   - Monitor for issues
   - Respond to user feedback
   - Plan next version

## Package Structure for PyPI

After cleanup, the published package will contain:

```
agentdk/
├── src/agentdk/           # Core library
│   ├── __init__.py
│   ├── agent/
│   ├── core/
│   └── exceptions.py
├── examples/              # Essential examples only
│   ├── agent.py
│   ├── simple_agent.py
│   ├── subagent/
│   ├── docker-compose.yml
│   └── sql/
├── tests/                 # Unit tests
├── README.md              # Updated with usage examples
├── LICENSE                # MIT license
└── pyproject.toml         # Package configuration
```

This structure provides users with:
- ✅ Clean, production-ready library
- ✅ Essential usage examples
- ✅ Database setup for testing
- ✅ Clear documentation
- ✅ No development artifacts

## Success Criteria

Your package is ready when:
- ✅ `pip install agentdk` works
- ✅ Basic import succeeds: `from agentdk import EDAAgent`
- ✅ Examples run without errors
- ✅ Documentation is clear and helpful
- ✅ Package size is reasonable (<10MB)

Follow this guide step-by-step to ensure a smooth publication process! 