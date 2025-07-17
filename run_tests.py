#!/usr/bin/env python3
"""
Test runner script for validating the refactored backend code.
This script runs all tests and provides a comprehensive report.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def check_python_environment():
    """Check if Python environment is properly set up."""
    print("🔍 Checking Python environment...")
    
    # Check Python version
    code, stdout, stderr = run_command("python --version")
    if code == 0:
        print(f"✅ Python version: {stdout.strip()}")
    else:
        print(f"❌ Python check failed: {stderr}")
        return False
    
    # Check if pytest is available
    code, stdout, stderr = run_command("python -c 'import pytest; print(pytest.__version__)'")
    if code == 0:
        print(f"✅ Pytest version: {stdout.strip()}")
    else:
        print(f"❌ Pytest not available: {stderr}")
        return False
    
    return True

def check_imports():
    """Check if main modules can be imported."""
    print("\n🔍 Checking module imports...")
    
    modules_to_check = [
        "config",
        "models.image",
        "services.cache_service",
        "services.vision_service"
    ]
    
    all_imports_ok = True
    for module in modules_to_check:
        code, stdout, stderr = run_command(f"python -c 'import {module}; print(\"OK\")'")
        if code == 0:
            print(f"✅ {module}: OK")
        else:
            print(f"❌ {module}: {stderr}")
            all_imports_ok = False
    
    return all_imports_ok

def run_unit_tests():
    """Run unit tests."""
    print("\n🧪 Running unit tests...")
    
    code, stdout, stderr = run_command("python -m pytest tests/unit/ -v --tb=short")
    
    if code == 0:
        print("✅ Unit tests passed")
        return True, stdout
    else:
        print("❌ Unit tests failed")
        print(f"Error: {stderr}")
        return False, stderr

def run_integration_tests():
    """Run integration tests."""
    print("\n🔗 Running integration tests...")
    
    code, stdout, stderr = run_command("python -m pytest tests/integration/ -v --tb=short")
    
    if code == 0:
        print("✅ Integration tests passed")
        return True, stdout
    else:
        print("❌ Integration tests failed")
        print(f"Error: {stderr}")
        return False, stderr

def run_e2e_tests():
    """Run end-to-end tests."""
    print("\n🎯 Running end-to-end tests...")
    
    code, stdout, stderr = run_command("python -m pytest tests/e2e/ -v --tb=short")
    
    if code == 0:
        print("✅ E2E tests passed")
        return True, stdout
    else:
        print("❌ E2E tests failed")
        print(f"Error: {stderr}")
        return False, stderr

def run_all_tests():
    """Run all tests with coverage."""
    print("\n📊 Running all tests with coverage...")
    
    code, stdout, stderr = run_command("python -m pytest tests/ -v --cov=. --cov-report=term-missing")
    
    if code == 0:
        print("✅ All tests passed")
        return True, stdout
    else:
        print("❌ Some tests failed")
        print(f"Error: {stderr}")
        return False, stderr

def check_api_functionality():
    """Check basic API functionality."""
    print("\n🌐 Checking API functionality...")
    
    # Try to import and create the FastAPI app
    code, stdout, stderr = run_command("""
python -c "
try:
    from main import app
    print('FastAPI app created successfully')
    print(f'App routes: {len(app.routes)}')
except Exception as e:
    print(f'Error creating app: {e}')
    exit(1)
"
""")
    
    if code == 0:
        print("✅ API functionality check passed")
        print(stdout)
        return True
    else:
        print("❌ API functionality check failed")
        print(stderr)
        return False

def performance_check():
    """Basic performance check."""
    print("\n⚡ Running performance check...")
    
    start_time = time.time()
    
    # Check import time
    code, stdout, stderr = run_command("python -c 'import main'")
    
    end_time = time.time()
    import_time = end_time - start_time
    
    if code == 0 and import_time < 10:  # Should import within 10 seconds
        print(f"✅ Import performance: {import_time:.2f}s")
        return True
    else:
        print(f"❌ Import performance issue: {import_time:.2f}s")
        return False

def main():
    """Main test runner function."""
    print("🚀 Starting Backend Code Refactoring Validation")
    print("=" * 50)
    
    # Change to the correct directory
    os.chdir(Path(__file__).parent)
    
    results = {}
    
    # Run all checks
    results['environment'] = check_python_environment()
    results['imports'] = check_imports()
    results['api'] = check_api_functionality()
    results['performance'] = performance_check()
    
    # Run tests
    results['unit_tests'], unit_output = run_unit_tests()
    results['integration_tests'], integration_output = run_integration_tests()
    results['e2e_tests'], e2e_output = run_e2e_tests()
    results['all_tests'], all_output = run_all_tests()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All validation checks passed! Refactoring is successful.")
        return 0
    else:
        print("⚠️  Some validation checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())