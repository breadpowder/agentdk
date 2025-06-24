#!/usr/bin/env python3
"""
Cleanup script to remove unused, debug, and testing files from AgentDK project.
This prepares the codebase for production release and PyPI publication.
"""

import os
import shutil
from pathlib import Path
from typing import List, Set

# Files and directories to remove
UNUSED_FILES: List[str] = [
    # Debug and testing files in examples/
    "examples/test_prompt_consistency.py",
    "examples/test_response_consistency_manual.py", 
    "examples/test_mcp_details_focused.py",
    "examples/test_enhanced_mcp_logging.py",
    "examples/debug_wrap_tools_flow.py",
    "examples/debug_tool_wrapping.py",
    "examples/test_multiple_queries.py",
    "examples/test_logging_analysis.py", 
    "examples/test_john_smith_query.py",
    "examples/test_complete_fix.py",
    "examples/test_supervisor_fix.py",
    "examples/agentdk_testing_notebook.ipynb",
    
    # Documentation files that are internal
    "examples/RESPONSE_CONSISTENCY_FIX.md",
    
    # Development/feedback files
    "CODE_OPTIMIZATION_REPORT.md",
    "feedback_round_1.md",
    "design_doc.md",
    "SETUP.md",
    
    # Memory bank (internal development docs)
    "memory-bank/",
    
    # Build artifacts
    "dist/",
    ".venv/",
]

UNUSED_DIRECTORIES: List[str] = [
    # Pycache directories
    "examples/__pycache__/",
    "tests/__pycache__/", 
    "src/agentdk/__pycache__/",
    
    # Cursor IDE files
    ".cursor/",
]

# Files to keep in examples (core examples only)
KEEP_EXAMPLES: Set[str] = {
    "examples/agent.py",           # Main agent example
    "examples/simple_agent.py",    # Simple usage example  
    "examples/README.md",          # Examples documentation
    "examples/docker-compose.yml", # Database setup
    "examples/sql/",              # Database schema
    "examples/subagent/",         # Subagent implementations
    "examples/mysql_mcp_server/", # MCP server example
}

def should_keep_file(file_path: str) -> bool:
    """Check if a file should be kept based on the keep list."""
    for keep_pattern in KEEP_EXAMPLES:
        if file_path.startswith(keep_pattern):
            return True
    return False

def cleanup_unused_files(project_root: Path, dry_run: bool = True) -> None:
    """Remove unused files and directories from the project.
    
    Args:
        project_root: Root directory of the project
        dry_run: If True, only print what would be deleted
    """
    
    print("🧹 AgentDK Cleanup Script")
    print("=" * 50)
    print(f"Project root: {project_root}")
    print(f"Dry run: {dry_run}")
    print()
    
    removed_count = 0
    kept_count = 0
    
    # Remove specific files
    print("📁 Removing unused files:")
    print("-" * 30)
    
    for file_path in UNUSED_FILES:
        full_path = project_root / file_path
        
        if full_path.exists():
            if should_keep_file(file_path):
                print(f"⚠️  KEEPING (in keep list): {file_path}")
                kept_count += 1
                continue
                
            if dry_run:
                print(f"🗑️  WOULD DELETE: {file_path}")
            else:
                try:
                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                        print(f"🗑️  DELETED DIR: {file_path}")
                    else:
                        full_path.unlink()
                        print(f"🗑️  DELETED FILE: {file_path}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ ERROR deleting {file_path}: {e}")
        else:
            print(f"⚪ NOT FOUND: {file_path}")
    
    # Remove pycache directories
    print(f"\n🐍 Removing __pycache__ directories:")
    print("-" * 40)
    
    for root, dirs, files in os.walk(project_root):
        if '__pycache__' in dirs:
            pycache_path = Path(root) / '__pycache__'
            relative_path = pycache_path.relative_to(project_root)
            
            if dry_run:
                print(f"🗑️  WOULD DELETE: {relative_path}")
            else:
                try:
                    shutil.rmtree(pycache_path)
                    print(f"🗑️  DELETED: {relative_path}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ ERROR deleting {relative_path}: {e}")
    
    # Summary
    print(f"\n📊 Cleanup Summary:")
    print("-" * 20)
    print(f"Files/dirs that would be removed: {len(UNUSED_FILES)}")
    print(f"Files/dirs kept (in keep list): {kept_count}")
    
    if not dry_run:
        print(f"Files/dirs actually removed: {removed_count}")
        print("✅ Cleanup completed!")
    else:
        print("ℹ️  This was a dry run. Use --execute to actually delete files.")

def main():
    """Main function with command line argument handling."""
    import sys
    
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    
    # Check for --execute flag
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No files will be deleted")
        print("   Use --execute flag to actually delete files")
        print()
    
    cleanup_unused_files(project_root, dry_run=dry_run)
    
    if dry_run:
        print(f"\n🚀 To execute the cleanup, run:")
        print(f"   python {__file__} --execute")

if __name__ == "__main__":
    main() 