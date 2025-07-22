# Release and Publish Command

This command automates the complete release and publish process for AgentDK to PyPI.

## Command Usage

When the user requests to release and publish a new version, follow this workflow:

### 1. Get Version Input
Ask the user for the version number:
```
What version would you like to release? (e.g., 0.3.1, 0.4.0, 1.0.0)
```

### 2. Update pyproject.toml
Update the version in pyproject.toml file:
```bash
# Read current version first
Read pyproject.toml to see current version

# Update version using Edit tool
Edit pyproject.toml - change version line from old version to new version
```

### 3. Commit and Tag
Create commit and tag for the release:
```bash
# Check git status
git status

# Commit the version change
git commit -m "$(cat <<'EOF'
Release v{VERSION}

Version bump from {OLD_VERSION} to {NEW_VERSION} in pyproject.toml

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Create git tag
git tag v{VERSION}

# Verify tag was created
git tag -l | grep v{VERSION}
```

### 4. Publish to PyPI
Run the publish script with automated responses:
```bash
# Publish to PyPI (responds N to version update, y to publish)
echo -e "N\ny" | python scripts/publish_to_pypi.py --version {VERSION} --production
```

### 5. Verify Publication
Verify the package was published successfully:
```bash
# Test basic import
python -c "import agentdk; print('✅ AgentDK imported successfully')"
```

## Complete Workflow Template

```bash
# 1. Update pyproject.toml version
# (Use Edit tool to change version)

# 2. Commit and tag
git status
git commit -m "Release v{VERSION}"
git tag v{VERSION}

# 3. Publish to PyPI
echo -e "N\ny" | python scripts/publish_to_pypi.py --version {VERSION} --production

# 4. Verify
python -c "import agentdk; print('✅ AgentDK imported successfully')"
```

## Success Criteria

The release is successful when:
- ✅ pyproject.toml version is updated
- ✅ Git commit and tag are created
- ✅ Package is published to PyPI
- ✅ Package can be imported successfully
- ✅ Publication script reports success

## Notes

- The publish script runs tests, builds the package, and publishes automatically
- The script prompts for version update confirmation (respond "N" since we already updated)
- The script prompts for publish confirmation (respond "y" to proceed)
- Always verify the import works after publication
- The package becomes available immediately on PyPI as `pip install agentdk`

## Prerequisites

- PyPI authentication must be configured (API tokens in ~/.pypirc or environment variables)
- Git repository must be in clean state
- All tests must pass
- uv package manager must be installed