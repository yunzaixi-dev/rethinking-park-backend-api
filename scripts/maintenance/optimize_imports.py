#!/usr/bin/env python3
"""
Import optimization script to fix circular imports and improve module loading.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ImportAnalyzer(ast.NodeVisitor):
    """Analyze imports in Python files."""
    
    def __init__(self):
        self.imports = []
        self.from_imports = []
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
    
    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.from_imports.append((node.module, alias.name))


def analyze_file_imports(file_path: Path) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Analyze imports in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)
        
        return analyzer.imports, analyzer.from_imports
    except Exception as e:
        print(f"Warning: Could not analyze {file_path}: {e}")
        return [], []


def find_circular_imports(project_root: Path) -> List[Tuple[str, str]]:
    """Find potential circular import issues."""
    # Get all Python files
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', 
                    'venv', '.venv', 'node_modules', 'dist', 'build'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    # Build import graph
    import_graph = {}
    
    for file_path in python_files:
        relative_path = file_path.relative_to(project_root)
        module_name = str(relative_path).replace('/', '.').replace('.py', '')
        
        imports, from_imports = analyze_file_imports(file_path)
        
        # Convert to module names
        all_imports = set()
        for imp in imports:
            all_imports.add(imp)
        
        for module, name in from_imports:
            all_imports.add(module)
        
        import_graph[module_name] = all_imports
    
    # Find circular dependencies (simplified check)
    circular_imports = []
    
    for module, imports in import_graph.items():
        for imported_module in imports:
            if imported_module in import_graph:
                if module in import_graph[imported_module]:
                    circular_imports.append((module, imported_module))
    
    return circular_imports


def optimize_imports_in_file(file_path: Path) -> bool:
    """Optimize imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find import section
        import_start = -1
        import_end = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')) and import_start == -1:
                import_start = i
            elif import_start != -1 and not stripped.startswith(('import ', 'from ')) and stripped and not stripped.startswith('#'):
                import_end = i
                break
        
        if import_start == -1:
            return False
        
        if import_end == -1:
            import_end = len(lines)
        
        # Extract imports
        import_lines = lines[import_start:import_end]
        other_lines = lines[:import_start] + lines[import_end:]
        
        # Categorize imports
        stdlib_imports = []
        third_party_imports = []
        local_imports = []
        
        stdlib_modules = {
            'os', 'sys', 'json', 'time', 'datetime', 'typing', 'pathlib',
            'asyncio', 'logging', 'collections', 'functools', 'itertools',
            'hashlib', 'uuid', 'base64', 'io', 'tempfile', 'concurrent',
            'unittest', 'contextlib', 're'
        }
        
        for line in import_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # Determine category
            if stripped.startswith('from '):
                module = stripped.split()[1].split('.')[0]
            else:
                module = stripped.split()[1].split('.')[0]
            
            if module in stdlib_modules:
                stdlib_imports.append(line)
            elif module in ['app', 'services', 'models']:
                local_imports.append(line)
            else:
                third_party_imports.append(line)
        
        # Sort within categories
        stdlib_imports.sort()
        third_party_imports.sort()
        local_imports.sort()
        
        # Rebuild import section
        new_import_lines = []
        
        if stdlib_imports:
            new_import_lines.extend(stdlib_imports)
            new_import_lines.append('\n')
        
        if third_party_imports:
            new_import_lines.extend(third_party_imports)
            new_import_lines.append('\n')
        
        if local_imports:
            new_import_lines.extend(local_imports)
            new_import_lines.append('\n')
        
        # Combine everything
        new_lines = other_lines[:import_start] + new_import_lines + other_lines[import_start:]
        
        # Write back if changed
        if new_lines != lines:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
        
    except Exception as e:
        print(f"Warning: Could not optimize imports in {file_path}: {e}")
        return False
    
    return False


def main():
    """Main function to optimize imports."""
    print("🔄 Optimizing imports and checking for circular dependencies...")
    
    project_root = Path(__file__).parent.parent.parent
    
    # Find circular imports
    print("🔍 Checking for circular imports...")
    circular_imports = find_circular_imports(project_root)
    
    if circular_imports:
        print("⚠️  Found potential circular imports:")
        for module1, module2 in circular_imports:
            print(f"  {module1} ↔ {module2}")
    else:
        print("✅ No obvious circular imports found")
    
    # Optimize imports in key files
    key_files = [
        "app/main.py",
        "app/api/v1/router.py",
        "app/config/settings.py",
        "services/enhanced_vision_service.py",
        "services/cache_service.py",
    ]
    
    optimized_count = 0
    for file_path in key_files:
        full_path = project_root / file_path
        if full_path.exists():
            if optimize_imports_in_file(full_path):
                print(f"✅ Optimized imports in {file_path}")
                optimized_count += 1
    
    print(f"📊 Optimized imports in {optimized_count} files")


if __name__ == "__main__":
    main()