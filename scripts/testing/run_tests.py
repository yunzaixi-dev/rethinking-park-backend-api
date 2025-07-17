#!/usr/bin/env python3
"""
Advanced test runner script for the rethinking-park-backend-api project.
Provides flexible test execution with various options and reporting.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


class TestRunner:
    """Advanced test runner with multiple execution modes."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent  # Go up two levels from scripts/testing/
        self.tests_dir = self.base_dir / "tests"
        
    def run_command(self, cmd, capture_output=False):
        """Run a shell command."""
        print(f"🔄 Running: {' '.join(cmd)}")
        try:
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
                return result.returncode == 0, result.stdout, result.stderr
            else:
                result = subprocess.run(cmd, cwd=self.base_dir)
                return result.returncode == 0, "", ""
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return False, "", str(e)
    
    def run_unit_tests(self, verbose=True):
        """Run unit tests."""
        print("🧪 Running unit tests...")
        cmd = ["python", "-m", "pytest", "tests/unit/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_integration_tests(self, verbose=True):
        """Run integration tests."""
        print("🔗 Running integration tests...")
        cmd = ["python", "-m", "pytest", "tests/integration/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_e2e_tests(self, verbose=True):
        """Run end-to-end tests."""
        print("🌐 Running end-to-end tests...")
        cmd = ["python", "-m", "pytest", "tests/e2e/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_all_tests(self, verbose=True):
        """Run all tests."""
        print("🚀 Running all tests...")
        cmd = ["python", "-m", "pytest", "tests/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_tests_with_coverage(self, min_coverage=70):
        """Run tests with coverage reporting."""
        print(f"📊 Running tests with coverage (minimum {min_coverage}%)...")
        cmd = [
            "python", "-m", "pytest",
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            f"--cov-fail-under={min_coverage}",
            "tests/"
        ]
        return self.run_command(cmd)
    
    def run_fast_tests(self, verbose=True):
        """Run fast tests only (exclude slow tests)."""
        print("⚡ Running fast tests...")
        cmd = ["python", "-m", "pytest", "-m", "not slow", "tests/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_slow_tests(self, verbose=True):
        """Run slow tests only."""
        print("🐌 Running slow tests...")
        cmd = ["python", "-m", "pytest", "-m", "slow", "tests/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_tests_by_marker(self, marker, verbose=True):
        """Run tests by specific marker."""
        print(f"🏷️  Running tests with marker: {marker}")
        cmd = ["python", "-m", "pytest", "-m", marker, "tests/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_specific_test(self, test_path, verbose=True):
        """Run a specific test file or test function."""
        print(f"🎯 Running specific test: {test_path}")
        cmd = ["python", "-m", "pytest", test_path]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def lint_code(self):
        """Run code linting."""
        print("🔍 Running code linting...")
        cmd = ["flake8", ".", "--count", "--select=E9,F63,F7,F82", "--show-source", "--statistics"]
        return self.run_command(cmd)
    
    def format_code(self):
        """Format code using black."""
        print("✨ Formatting code...")
        cmd = ["black", ".", "--line-length", "100"]
        return self.run_command(cmd)
    
    def clean_test_artifacts(self):
        """Clean test artifacts and cache files."""
        print("🧹 Cleaning test artifacts...")
        artifacts = [
            "htmlcov",
            ".coverage",
            ".pytest_cache",
            "*.egg-info"
        ]
        
        for artifact in artifacts:
            if artifact.startswith("*"):
                # Handle glob patterns
                import glob
                for path in glob.glob(artifact):
                    if os.path.isdir(path):
                        import shutil
                        shutil.rmtree(path)
                        print(f"  Removed directory: {path}")
                    elif os.path.isfile(path):
                        os.remove(path)
                        print(f"  Removed file: {path}")
            else:
                path = Path(artifact)
                if path.exists():
                    if path.is_dir():
                        import shutil
                        shutil.rmtree(path)
                        print(f"  Removed directory: {path}")
                    else:
                        path.unlink()
                        print(f"  Removed file: {path}")
        
        # Clean __pycache__ directories
        for pycache in Path(".").rglob("__pycache__"):
            import shutil
            shutil.rmtree(pycache)
            print(f"  Removed cache: {pycache}")
        
        # Clean .pyc files
        for pyc_file in Path(".").rglob("*.pyc"):
            pyc_file.unlink()
            print(f"  Removed: {pyc_file}")
    
    def check_test_structure(self):
        """Check if test structure is properly organized."""
        print("📁 Checking test structure...")
        
        required_dirs = [
            "tests/unit",
            "tests/integration", 
            "tests/e2e",
            "tests/unit/test_models",
            "tests/unit/test_services",
            "tests/unit/test_utils",
            "tests/integration/test_api",
            "tests/integration/test_services",
            "tests/e2e/test_workflows"
        ]
        
        required_files = [
            "tests/__init__.py",
            "tests/conftest.py",
            "tests/utils.py",
            "tests/test_config.py",
            "pytest.ini"
        ]
        
        all_good = True
        
        for dir_path in required_dirs:
            if not (self.base_dir / dir_path).exists():
                print(f"  ❌ Missing directory: {dir_path}")
                all_good = False
            else:
                print(f"  ✅ Directory exists: {dir_path}")
        
        for file_path in required_files:
            if not (self.base_dir / file_path).exists():
                print(f"  ❌ Missing file: {file_path}")
                all_good = False
            else:
                print(f"  ✅ File exists: {file_path}")
        
        if all_good:
            print("🎉 Test structure is properly organized!")
        else:
            print("⚠️  Test structure needs attention.")
        
        return all_good


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="Advanced test runner for rethinking-park-backend-api")
    
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--slow", action="store_true", help="Run slow tests only")
    parser.add_argument("--marker", type=str, help="Run tests with specific marker")
    parser.add_argument("--test", type=str, help="Run specific test file or function")
    parser.add_argument("--lint", action="store_true", help="Run code linting")
    parser.add_argument("--format", action="store_true", help="Format code")
    parser.add_argument("--clean", action="store_true", help="Clean test artifacts")
    parser.add_argument("--check-structure", action="store_true", help="Check test structure")
    parser.add_argument("--quiet", action="store_true", help="Run in quiet mode")
    parser.add_argument("--min-coverage", type=int, default=70, help="Minimum coverage percentage")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    verbose = not args.quiet
    success = True
    
    try:
        if args.clean:
            runner.clean_test_artifacts()
        
        if args.check_structure:
            success &= runner.check_test_structure()
        
        if args.lint:
            success &= runner.lint_code()[0]
        
        if args.format:
            success &= runner.format_code()[0]
        
        if args.unit:
            success &= runner.run_unit_tests(verbose)[0]
        
        if args.integration:
            success &= runner.run_integration_tests(verbose)[0]
        
        if args.e2e:
            success &= runner.run_e2e_tests(verbose)[0]
        
        if args.all:
            success &= runner.run_all_tests(verbose)[0]
        
        if args.coverage:
            success &= runner.run_tests_with_coverage(args.min_coverage)[0]
        
        if args.fast:
            success &= runner.run_fast_tests(verbose)[0]
        
        if args.slow:
            success &= runner.run_slow_tests(verbose)[0]
        
        if args.marker:
            success &= runner.run_tests_by_marker(args.marker, verbose)[0]
        
        if args.test:
            success &= runner.run_specific_test(args.test, verbose)[0]
        
        # If no specific action is specified, run all tests
        if not any([args.unit, args.integration, args.e2e, args.all, args.coverage, 
                   args.fast, args.slow, args.marker, args.test, args.lint, 
                   args.format, args.clean, args.check_structure]):
            success &= runner.run_all_tests(verbose)[0]
        
        if success:
            print("\n🎉 All operations completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some operations failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()