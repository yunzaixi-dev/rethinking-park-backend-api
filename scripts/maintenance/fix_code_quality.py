#!/usr/bin/env python3
"""
Code quality improvement script.

This script automatically fixes common code quality issues identified by linting tools.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set


def run_command(command: List[str], cwd: str = None) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def remove_unused_imports(file_path: Path) -> bool:
    """Remove unused imports from a Python file using autoflake."""
    command = [
        "python", "-m", "autoflake",
        "--remove-all-unused-imports",
        "--remove-unused-variables",
        "--in-place",
        str(file_path)
    ]
    
    exit_code, _, stderr = run_command(command)
    if exit_code != 0:
        print(f"Warning: Failed to remove unused imports from {file_path}: {stderr}")
        return False
    return True


def fix_import_order(file_path: Path) -> bool:
    """Fix import order using isort."""
    command = ["python", "-m", "isort", str(file_path)]
    exit_code, _, stderr = run_command(command)
    if exit_code != 0:
        print(f"Warning: Failed to fix imports in {file_path}: {stderr}")
        return False
    return True


def format_code(file_path: Path) -> bool:
    """Format code using black."""
    command = ["python", "-m", "black", str(file_path)]
    exit_code, _, stderr = run_command(command)
    if exit_code != 0:
        print(f"Warning: Failed to format {file_path}: {stderr}")
        return False
    return True


def add_missing_docstrings(file_path: Path) -> bool:
    """Add basic docstrings to functions and classes missing them."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            print(f"Warning: Syntax error in {file_path}, skipping docstring fixes")
            return False
        
        lines = content.split('\n')
        modified = False
        
        # Find functions and classes without docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Skip private methods and functions
                if node.name.startswith('_') and not node.name.startswith('__'):
                    continue
                
                # Check if it already has a docstring
                if (node.body and 
                    isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    continue
                
                # Add a basic docstring
                line_num = node.lineno - 1
                indent = len(lines[line_num]) - len(lines[line_num].lstrip())
                
                if isinstance(node, ast.ClassDef):
                    docstring = f'{" " * (indent + 4)}"""Class {node.name}."""'
                else:
                    docstring = f'{" " * (indent + 4)}"""Function {node.name}."""'
                
                # Insert the docstring after the function/class definition
                if line_num + 1 < len(lines):
                    lines.insert(line_num + 1, docstring)
                    modified = True
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return True
        
    except Exception as e:
        print(f"Warning: Failed to add docstrings to {file_path}: {e}")
        return False
    
    return False


def fix_line_length_issues(file_path: Path) -> bool:
    """Fix basic line length issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        new_lines = []
        
        for line in lines:
            # Skip lines that are already within limit
            if len(line.rstrip()) <= 88:
                new_lines.append(line)
                continue
            
            # Try to fix simple cases
            stripped = line.rstrip()
            
            # Fix long import lines
            if stripped.startswith('from ') and ' import ' in stripped:
                parts = stripped.split(' import ')
                if len(parts) == 2:
                    module = parts[0]
                    imports = parts[1].split(', ')
                    if len(imports) > 1:
                        # Split into multiple lines
                        new_lines.append(f"{module} import (\n")
                        for imp in imports:
                            new_lines.append(f"    {imp.strip()},\n")
                        new_lines.append(")\n")
                        modified = True
                        continue
            
            # For other long lines, just add them as-is for now
            # (Black will handle most formatting)
            new_lines.append(line)
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
        
    except Exception as e:
        print(f"Warning: Failed to fix line length in {file_path}: {e}")
        return False
    
    return False


def get_python_files(directory: Path) -> List[Path]:
    """Get all Python files in a directory."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', 
                    'venv', '.venv', 'node_modules', 'dist', 'build'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    return python_files


def main():
    """Main function to fix code quality issues."""
    print("🔧 Starting code quality improvements...")
    
    # Get the project root
    project_root = Path(__file__).parent.parent.parent
    
    # Install required tools
    print("📦 Installing required tools...")
    tools = ["autoflake", "isort", "black"]
    for tool in tools:
        exit_code, _, stderr = run_command([sys.executable, "-m", "pip", "install", tool])
        if exit_code != 0:
            print(f"Warning: Failed to install {tool}: {stderr}")
    
    # Get all Python files
    directories_to_fix = ["app", "services", "models", "tests"]
    all_files = []
    
    for directory in directories_to_fix:
        dir_path = project_root / directory
        if dir_path.exists():
            all_files.extend(get_python_files(dir_path))
    
    print(f"📁 Found {len(all_files)} Python files to process")
    
    # Process each file
    fixed_files = 0
    for file_path in all_files:
        print(f"🔄 Processing {file_path.relative_to(project_root)}")
        
        file_modified = False
        
        # 1. Remove unused imports
        if remove_unused_imports(file_path):
            file_modified = True
        
        # 2. Add missing docstrings (basic ones)
        if add_missing_docstrings(file_path):
            file_modified = True
        
        # 3. Fix import order
        if fix_import_order(file_path):
            file_modified = True
        
        # 4. Format code
        if format_code(file_path):
            file_modified = True
        
        if file_modified:
            fixed_files += 1
    
    print(f"✅ Code quality improvements completed!")
    print(f"📊 Modified {fixed_files} files")
    
    # Run final quality check
    print("\n🔍 Running final quality check...")
    exit_code, stdout, stderr = run_command(
        ["make", "lint-flake8"], 
        cwd=str(project_root)
    )
    
    if exit_code == 0:
        print("✅ All quality checks passed!")
    else:
        print("⚠️  Some quality issues remain. Check the output above.")
        print("You may need to manually fix complex issues.")


if __name__ == "__main__":
    main()