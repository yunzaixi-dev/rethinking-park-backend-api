#!/usr/bin/env python3
"""
Structural validation for backend refactoring.
This script validates the refactoring structure without triggering configuration validation.
"""

import os
import sys
from pathlib import Path

class StructuralValidator:
    """Validates the structural aspects of the refactoring."""
    
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
        
        existing_dirs = []
        missing_dirs = []
        
        for dir_path in required_dirs:
            full_path = self.base_path / dir_path
            if full_path.exists():
                existing_dirs.append(dir_path)
            else:
                missing_dirs.append(dir_path)
        
        print(f"✅ Existing directories: {len(existing_dirs)}/{len(required_dirs)}")
        for dir_path in existing_dirs:
            print(f"   ✓ {dir_path}")
            
        if missing_dirs:
            print(f"❌ Missing directories: {len(missing_dirs)}")
            for dir_path in missing_dirs:
                print(f"   ✗ {dir_path}")
        
        return len(missing_dirs) == 0
    
    def validate_key_files(self):
        """Validate that key files exist."""
        print("\n📁 Validating key files...")
        
        key_files = {
            "Application Entry": [
                "app/__init__.py",
                "app/main.py"
            ],
            "Configuration": [
                "app/config/__init__.py",
                "app/config/settings.py",
                "app/config/base.py"
            ],
            "API Structure": [
                "app/api/__init__.py",
                "app/api/v1/__init__.py",
                "app/api/v1/router.py"
            ],
            "Core Components": [
                "app/core/__init__.py",
                "app/core/exceptions.py",
                "app/core/middleware.py"
            ],
            "Models": [
                "app/models/__init__.py",
                "app/models/base.py",
                "app/models/image.py"
            ],
            "Services": [
                "app/services/__init__.py",
                "app/services/base.py",
                "app/services/dependencies.py"
            ],
            "Testing": [
                "tests/__init__.py",
                "tests/conftest.py",
                "pytest.ini"
            ],
            "Project Config": [
                "pyproject.toml",
                "requirements/base.txt",
                "requirements/dev.txt"
            ]
        }
        
        all_categories_valid = True
        
        for category, files in key_files.items():
            print(f"\n  {category}:")
            category_valid = True
            
            for file_path in files:
                full_path = self.base_path / file_path
                if full_path.exists():
                    print(f"    ✅ {file_path}")
                else:
                    print(f"    ❌ {file_path}")
                    category_valid = False
            
            if not category_valid:
                all_categories_valid = False
        
        return all_categories_valid
    
    def validate_test_organization(self):
        """Validate test file organization."""
        print("\n🧪 Validating test organization...")
        
        test_structure = {
            "tests/unit": ["test_models", "test_services", "test_utils", "test_core"],
            "tests/integration": ["test_api", "test_services"],
            "tests/e2e": ["test_workflows"]
        }
        
        all_valid = True
        
        for test_dir, expected_subdirs in test_structure.items():
            test_path = self.base_path / test_dir
            print(f"\n  {test_dir}:")
            
            if not test_path.exists():
                print(f"    ❌ Directory missing")
                all_valid = False
                continue
            
            for subdir in expected_subdirs:
                subdir_path = test_path / subdir
                if subdir_path.exists():
                    # Count test files in subdirectory
                    test_files = list(subdir_path.glob("test_*.py"))
                    print(f"    ✅ {subdir} ({len(test_files)} test files)")
                else:
                    print(f"    ❌ {subdir}")
                    all_valid = False
        
        return all_valid
    
    def validate_service_organization(self):
        """Validate service organization."""
        print("\n🔧 Validating service organization...")
        
        # Check old services directory (should still exist for compatibility)
        old_services = self.base_path / "services"
        new_services = self.base_path / "app" / "services"
        
        print(f"  Legacy services directory: {'✅' if old_services.exists() else '❌'}")
        print(f"  New services directory: {'✅' if new_services.exists() else '❌'}")
        
        # Check service subdirectories
        service_subdirs = ["cache", "external", "image", "vision"]
        all_subdirs_exist = True
        
        for subdir in service_subdirs:
            subdir_path = new_services / subdir
            if subdir_path.exists():
                print(f"  ✅ app/services/{subdir}")
            else:
                print(f"  ❌ app/services/{subdir}")
                all_subdirs_exist = False
        
        return old_services.exists() and new_services.exists() and all_subdirs_exist
    
    def validate_configuration_files(self):
        """Validate configuration files."""
        print("\n⚙️  Validating configuration files...")
        
        config_files = [
            ("pytest.ini", "Test configuration"),
            ("pyproject.toml", "Project configuration"),
            (".gitignore", "Git ignore rules"),
            ("requirements/base.txt", "Base dependencies"),
            ("requirements/dev.txt", "Development dependencies"),
            ("requirements/prod.txt", "Production dependencies"),
            ("Makefile", "Build automation"),
            ("README.md", "Project documentation")
        ]
        
        valid_configs = 0
        
        for config_file, description in config_files:
            file_path = self.base_path / config_file
            if file_path.exists() and file_path.stat().st_size > 0:
                print(f"  ✅ {config_file} - {description}")
                valid_configs += 1
            else:
                print(f"  ❌ {config_file} - {description}")
        
        return valid_configs >= len(config_files) * 0.8  # 80% should exist
    
    def validate_deployment_structure(self):
        """Validate deployment structure."""
        print("\n🚀 Validating deployment structure...")
        
        deployment_files = [
            "deployment/docker-compose.dev.yml",
            "deployment/docker-compose.staging.yml",
            "deployment/nginx.conf",
            "deployment/production.yml",
            "Dockerfile"
        ]
        
        valid_deployments = 0
        
        for deploy_file in deployment_files:
            file_path = self.base_path / deploy_file
            if file_path.exists():
                print(f"  ✅ {deploy_file}")
                valid_deployments += 1
            else:
                print(f"  ❌ {deploy_file}")
        
        return valid_deployments >= len(deployment_files) * 0.6  # 60% should exist
    
    def check_file_sizes(self):
        """Check if main files have been properly refactored."""
        print("\n📊 Checking refactoring effectiveness...")
        
        # Compare old vs new main.py
        old_main = self.base_path / "main.py"
        new_main = self.base_path / "app" / "main.py"
        
        if old_main.exists() and new_main.exists():
            old_size = old_main.stat().st_size
            new_size = new_main.stat().st_size
            
            print(f"  Original main.py: {old_size:,} bytes")
            print(f"  Refactored app/main.py: {new_size:,} bytes")
            
            if new_size < old_size:
                reduction = ((old_size - new_size) / old_size) * 100
                print(f"  ✅ Size reduction: {reduction:.1f}%")
                return True
            else:
                print(f"  ⚠️  No size reduction achieved")
                return False
        else:
            print(f"  ⚠️  Cannot compare file sizes")
            return True  # Don't fail if files don't exist
    
    def count_python_files(self):
        """Count Python files in different directories."""
        print("\n📈 Python file distribution:")
        
        directories = [
            "app",
            "services", 
            "tests",
            "scripts"
        ]
        
        total_files = 0
        
        for directory in directories:
            dir_path = self.base_path / directory
            if dir_path.exists():
                py_files = list(dir_path.rglob("*.py"))
                print(f"  {directory}: {len(py_files)} Python files")
                total_files += len(py_files)
            else:
                print(f"  {directory}: Directory not found")
        
        print(f"  Total: {total_files} Python files")
        return total_files > 0
    
    def run_validation(self):
        """Run all structural validation checks."""
        print("🔍 Backend Refactoring Structural Validation")
        print("=" * 50)
        
        # Run all validation checks
        self.results['directory_structure'] = self.validate_directory_structure()
        self.results['key_files'] = self.validate_key_files()
        self.results['test_organization'] = self.validate_test_organization()
        self.results['service_organization'] = self.validate_service_organization()
        self.results['configuration_files'] = self.validate_configuration_files()
        self.results['deployment_structure'] = self.validate_deployment_structure()
        self.results['refactoring_effectiveness'] = self.check_file_sizes()
        self.results['file_distribution'] = self.count_python_files()
        
        # Generate summary
        self.generate_summary()
        
        return sum(self.results.values()) >= len(self.results) * 0.8
    
    def generate_summary(self):
        """Generate validation summary."""
        print("\n" + "=" * 50)
        print("📋 STRUCTURAL VALIDATION SUMMARY")
        print("=" * 50)
        
        passed = sum(self.results.values())
        total = len(self.results)
        
        for check, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{check.replace('_', ' ').title()}: {status}")
        
        score = (passed / total) * 100
        print(f"\nStructural Score: {passed}/{total} ({score:.1f}%)")
        
        if score >= 90:
            print("🎉 Excellent! Refactoring structure is complete.")
        elif score >= 80:
            print("✅ Good! Refactoring structure is mostly complete.")
        elif score >= 60:
            print("⚠️  Fair. Some structural issues need attention.")
        else:
            print("❌ Poor. Significant structural issues found.")

def main():
    """Main validation function."""
    validator = StructuralValidator()
    success = validator.run_validation()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())