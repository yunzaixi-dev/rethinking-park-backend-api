#!/usr/bin/env python3
"""
Validation script for backend code refactoring.
This script validates that the refactoring has been completed successfully.
"""

import os
import sys
from pathlib import Path
import importlib.util
import ast

class RefactoringValidator:
    """Validates the backend refactoring results."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.results = {}
        
    def validate_directory_structure(self):
        """Validate that the new directory structure is in place."""
        print("🏗️  Validating directory structure...")
        
        required_dirs = [
            "app",
            "app/api",
            "app/api/v1",
            "app/api/v1/endpoints",
            "app/config",
            "app/core", 
            "app/models",
            "app/services",
            "app/services/cache",
            "app/services/external",
            "app/services/image",
            "app/services/vision",
            "app/utils",
            "tests",
            "tests/unit",
            "tests/integration", 
            "tests/e2e",
            "scripts",
            "deployment",
            "docs",
            "config",
            "requirements"
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.base_path / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            print(f"❌ Missing directories: {missing_dirs}")
            return False
        else:
            print(f"✅ All {len(required_dirs)} required directories exist")
            return True
    
    def validate_file_structure(self):
        """Validate that key files are in the correct locations."""
        print("\n📁 Validating file structure...")
        
        required_files = [
            "app/__init__.py",
            "app/main.py",
            "app/config/settings.py",
            "app/api/v1/router.py",
            "app/core/exceptions.py",
            "app/models/base.py",
            "app/services/base.py",
            "tests/conftest.py",
            "pytest.ini",
            "pyproject.toml",
            "requirements/base.txt",
            "requirements/dev.txt",
            "requirements/prod.txt"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.base_path / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False
        else:
            print(f"✅ All {len(required_files)} required files exist")
            return True
    
    def validate_imports(self):
        """Validate that key modules can be imported."""
        print("\n🔗 Validating module imports...")
        
        modules_to_test = [
            ("app.config.settings", "settings"),
            ("app.models.base", "BaseModel"),
            ("app.services.base", "BaseService"),
            ("app.core.exceptions", "APIException")
        ]
        
        import_results = []
        for module_name, item_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, item_name):
                    print(f"✅ {module_name}.{item_name}")
                    import_results.append(True)
                else:
                    print(f"❌ {module_name}.{item_name} not found")
                    import_results.append(False)
            except ImportError as e:
                print(f"❌ {module_name} import failed: {e}")
                import_results.append(False)
        
        return all(import_results)
    
    def validate_test_structure(self):
        """Validate test organization."""
        print("\n🧪 Validating test structure...")
        
        test_categories = {
            "unit": ["test_models", "test_services", "test_utils"],
            "integration": ["test_api", "test_services"],
            "e2e": ["test_workflows"]
        }
        
        all_valid = True
        for category, expected_dirs in test_categories.items():
            category_path = self.base_path / "tests" / category
            if not category_path.exists():
                print(f"❌ Test category missing: {category}")
                all_valid = False
                continue
                
            for expected_dir in expected_dirs:
                dir_path = category_path / expected_dir
                if dir_path.exists():
                    print(f"✅ {category}/{expected_dir}")
                else:
                    print(f"❌ {category}/{expected_dir} missing")
                    all_valid = False
        
        return all_valid
    
    def validate_configuration_files(self):
        """Validate configuration files."""
        print("\n⚙️  Validating configuration files...")
        
        config_files = [
            "pytest.ini",
            "pyproject.toml", 
            ".gitignore",
            "requirements/base.txt",
            "requirements/dev.txt",
            "requirements/prod.txt"
        ]
        
        all_valid = True
        for config_file in config_files:
            file_path = self.base_path / config_file
            if file_path.exists() and file_path.stat().st_size > 0:
                print(f"✅ {config_file}")
            else:
                print(f"❌ {config_file} missing or empty")
                all_valid = False
        
        return all_valid
    
    def validate_code_quality(self):
        """Validate code quality improvements."""
        print("\n📊 Validating code quality...")
        
        # Check if main.py has been refactored (should be smaller now)
        old_main = self.base_path / "main.py"
        new_main = self.base_path / "app" / "main.py"
        
        quality_checks = []
        
        if old_main.exists() and new_main.exists():
            old_size = old_main.stat().st_size
            new_size = new_main.stat().st_size
            
            if new_size < old_size:
                print(f"✅ main.py refactored (reduced from {old_size} to {new_size} bytes)")
                quality_checks.append(True)
            else:
                print(f"⚠️  main.py size not reduced ({old_size} -> {new_size} bytes)")
                quality_checks.append(False)
        
        # Check for proper __init__.py files
        init_files = [
            "app/__init__.py",
            "app/api/__init__.py",
            "app/config/__init__.py",
            "app/models/__init__.py",
            "app/services/__init__.py",
            "tests/__init__.py"
        ]
        
        init_count = 0
        for init_file in init_files:
            if (self.base_path / init_file).exists():
                init_count += 1
        
        if init_count == len(init_files):
            print(f"✅ All {len(init_files)} __init__.py files present")
            quality_checks.append(True)
        else:
            print(f"❌ Missing __init__.py files ({init_count}/{len(init_files)})")
            quality_checks.append(False)
        
        return all(quality_checks)
    
    def validate_documentation(self):
        """Validate documentation structure."""
        print("\n📚 Validating documentation...")
        
        doc_files = [
            "README.md",
            "docs/api/README.md",
            "docs/deployment/README.md", 
            "docs/development/README.md"
        ]
        
        doc_count = 0
        for doc_file in doc_files:
            if (self.base_path / doc_file).exists():
                doc_count += 1
                print(f"✅ {doc_file}")
            else:
                print(f"❌ {doc_file} missing")
        
        return doc_count >= len(doc_files) // 2  # At least half should exist
    
    def validate_deployment_structure(self):
        """Validate deployment configuration."""
        print("\n🚀 Validating deployment structure...")
        
        deployment_files = [
            "deployment/docker-compose.dev.yml",
            "deployment/docker-compose.staging.yml", 
            "deployment/nginx.conf",
            "deployment/production.yml"
        ]
        
        deployment_count = 0
        for deploy_file in deployment_files:
            if (self.base_path / deploy_file).exists():
                deployment_count += 1
                print(f"✅ {deploy_file}")
            else:
                print(f"❌ {deploy_file} missing")
        
        return deployment_count >= len(deployment_files) // 2
    
    def run_validation(self):
        """Run all validation checks."""
        print("🔍 Starting Backend Refactoring Validation")
        print("=" * 50)
        
        # Run all validation checks
        self.results['directory_structure'] = self.validate_directory_structure()
        self.results['file_structure'] = self.validate_file_structure()
        self.results['imports'] = self.validate_imports()
        self.results['test_structure'] = self.validate_test_structure()
        self.results['configuration'] = self.validate_configuration_files()
        self.results['code_quality'] = self.validate_code_quality()
        self.results['documentation'] = self.validate_documentation()
        self.results['deployment'] = self.validate_deployment_structure()
        
        # Generate summary
        self.generate_summary()
        
        return all(self.results.values())
    
    def generate_summary(self):
        """Generate validation summary."""
        print("\n" + "=" * 50)
        print("📋 REFACTORING VALIDATION SUMMARY")
        print("=" * 50)
        
        passed = 0
        total = len(self.results)
        
        for check, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{check.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
        
        print(f"\nOverall Score: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 Refactoring validation PASSED! All checks successful.")
        elif passed >= total * 0.8:
            print("✅ Refactoring validation mostly PASSED with minor issues.")
        else:
            print("⚠️  Refactoring validation FAILED. Please address the issues above.")

def main():
    """Main validation function."""
    validator = RefactoringValidator()
    success = validator.run_validation()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())