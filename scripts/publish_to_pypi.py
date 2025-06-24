#!/usr/bin/env python3
"""
Script to prepare and publish AgentDK to PyPI.
This handles version management, building, and publishing.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional
import toml
import re

def run_command(cmd: str, cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(
        cmd, 
        shell=True, 
        capture_output=True, 
        text=True, 
        cwd=cwd
    )
    return result.returncode, result.stdout, result.stderr

def get_current_version(pyproject_path: Path) -> str:
    """Get current version from pyproject.toml."""
    with open(pyproject_path, 'r') as f:
        data = toml.load(f)
    return data['project']['version']

def update_version(pyproject_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml."""
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Replace version line
    pattern = r'version\s*=\s*"[^"]*"'
    replacement = f'version = "{new_version}"'
    new_content = re.sub(pattern, replacement, content)
    
    with open(pyproject_path, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Updated version to {new_version}")

def validate_pyproject(pyproject_path: Path) -> bool:
    """Validate pyproject.toml for PyPI requirements."""
    print("📋 Validating pyproject.toml...")
    
    try:
        with open(pyproject_path, 'r') as f:
            data = toml.load(f)
        
        project = data.get('project', {})
        required_fields = ['name', 'version', 'description', 'authors', 'license']
        
        missing_fields = []
        for field in required_fields:
            if field not in project:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print("✅ pyproject.toml validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Error validating pyproject.toml: {e}")
        return False

def build_package(project_root: Path) -> bool:
    """Build the package using uv."""
    print("🏗️  Building package...")
    
    # Clean previous builds
    dist_dir = project_root / "dist"
    if dist_dir.exists():
        import shutil
        shutil.rmtree(dist_dir)
        print("🧹 Cleaned previous build artifacts")
    
    # Build with uv
    exit_code, stdout, stderr = run_command("uv build", cwd=project_root)
    
    if exit_code != 0:
        print(f"❌ Build failed:")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    print("✅ Package built successfully")
    return True

def run_tests(project_root: Path) -> bool:
    """Run tests before publishing."""
    print("🧪 Running tests...")
    
    exit_code, stdout, stderr = run_command("uv run pytest tests/ -v", cwd=project_root)
    
    if exit_code != 0:
        print(f"❌ Tests failed:")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    print("✅ All tests passed")
    return True

def publish_to_pypi(project_root: Path, test_pypi: bool = True) -> bool:
    """Publish package to PyPI or TestPyPI."""
    
    if test_pypi:
        print("🚀 Publishing to TestPyPI...")
        repository_url = "https://test.pypi.org/legacy/"
        index_url = "https://test.pypi.org/simple/"
    else:
        print("🚀 Publishing to PyPI...")
        repository_url = "https://upload.pypi.org/legacy/"
        index_url = "https://pypi.org/simple/"
    
    # Use uv to publish
    cmd = f"uv publish --repository-url {repository_url}"
    exit_code, stdout, stderr = run_command(cmd, cwd=project_root)
    
    if exit_code != 0:
        print(f"❌ Publishing failed:")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        return False
    
    print(f"✅ Published successfully to {'TestPyPI' if test_pypi else 'PyPI'}")
    return True

def verify_installation(package_name: str, test_pypi: bool = True) -> bool:
    """Verify package can be installed from PyPI."""
    print(f"🔍 Verifying installation...")
    
    if test_pypi:
        cmd = f"pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ {package_name}"
    else:
        cmd = f"pip install {package_name}"
    
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        print(f"❌ Installation verification failed:")
        print(f"STDERR: {stderr}")
        return False
    
    print("✅ Package installs successfully")
    return True

def main():
    """Main publication workflow."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Publish AgentDK to PyPI")
    parser.add_argument("--version", help="New version number (e.g., 0.1.0)")
    parser.add_argument("--test-pypi", action="store_true", help="Publish to TestPyPI instead of PyPI")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-build", action="store_true", help="Skip building (use existing build)")
    parser.add_argument("--production", action="store_true", help="Publish to production PyPI")
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"
    
    print("🚀 AgentDK PyPI Publication Script")
    print("=" * 50)
    print(f"Project root: {project_root}")
    print(f"Target: {'Production PyPI' if args.production else 'TestPyPI'}")
    print()
    
    # Step 1: Validate pyproject.toml
    if not validate_pyproject(pyproject_path):
        print("❌ Validation failed. Please fix pyproject.toml")
        sys.exit(1)
    
    # Step 2: Update version if provided
    if args.version:
        current_version = get_current_version(pyproject_path)
        print(f"Current version: {current_version}")
        print(f"New version: {args.version}")
        
        if input("Update version? (y/N): ").lower() == 'y':
            update_version(pyproject_path, args.version)
    
    # Step 3: Run tests
    if not args.skip_tests:
        if not run_tests(project_root):
            print("❌ Tests failed. Fix issues before publishing.")
            sys.exit(1)
    
    # Step 4: Build package
    if not args.skip_build:
        if not build_package(project_root):
            print("❌ Build failed. Fix issues before publishing.")
            sys.exit(1)
    
    # Step 5: Confirm publication
    target = "Production PyPI" if args.production else "TestPyPI"
    if input(f"Publish to {target}? (y/N): ").lower() != 'y':
        print("❌ Publication cancelled.")
        sys.exit(0)
    
    # Step 6: Publish
    if not publish_to_pypi(project_root, test_pypi=not args.production):
        print("❌ Publication failed.")
        sys.exit(1)
    
    # Step 7: Verify installation
    package_name = "agentdk"
    if not verify_installation(package_name, test_pypi=not args.production):
        print("⚠️  Installation verification failed, but package may still be published.")
    
    print("\n🎉 Publication completed successfully!")
    print(f"📦 Package: {package_name}")
    
    if args.production:
        print(f"🌍 Install with: pip install {package_name}")
    else:
        print(f"🧪 Install with: pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ {package_name}")

if __name__ == "__main__":
    main() 