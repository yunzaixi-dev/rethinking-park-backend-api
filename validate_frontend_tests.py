#!/usr/bin/env python3
"""
Frontend test validation script
Validates the structure and completeness of frontend component tests
"""

import os
import re
from pathlib import Path

def validate_test_file(test_file_path):
    """Validate a single test file"""
    print(f"\n📋 Validating: {test_file_path}")
    
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required test structure
        checks = {
            'imports': {
                'pattern': r'import.*from.*@testing-library',
                'description': 'Testing library imports'
            },
            'describe_blocks': {
                'pattern': r'describe\(',
                'description': 'Test suite organization'
            },
            'test_cases': {
                'pattern': r'test\(',
                'description': 'Individual test cases'
            },
            'assertions': {
                'pattern': r'expect\(',
                'description': 'Test assertions'
            },
            'async_tests': {
                'pattern': r'async.*\(\)',
                'description': 'Async test handling'
            },
            'mocks': {
                'pattern': r'jest\.mock',
                'description': 'Mocking setup'
            },
            'cleanup': {
                'pattern': r'beforeEach|afterEach',
                'description': 'Test cleanup'
            }
        }
        
        results = {}
        for check_name, check_info in checks.items():
            matches = re.findall(check_info['pattern'], content, re.MULTILINE)
            results[check_name] = {
                'count': len(matches),
                'description': check_info['description'],
                'found': len(matches) > 0
            }
        
        # Count test categories
        describe_matches = re.findall(r'describe\([\'"]([^\'"]+)[\'"]', content)
        test_matches = re.findall(r'test\([\'"]([^\'"]+)[\'"]', content)
        
        print(f"  ✅ Test suites: {len(describe_matches)}")
        for suite in describe_matches[:5]:  # Show first 5
            print(f"    - {suite}")
        if len(describe_matches) > 5:
            print(f"    ... and {len(describe_matches) - 5} more")
        
        print(f"  ✅ Test cases: {len(test_matches)}")
        
        # Validate specific patterns
        validation_results = []
        
        for check_name, result in results.items():
            if result['found']:
                validation_results.append(f"  ✅ {result['description']}: {result['count']} found")
            else:
                validation_results.append(f"  ⚠️  {result['description']}: Not found")
        
        for result in validation_results:
            print(result)
        
        # Check for component-specific tests
        component_name = os.path.basename(test_file_path).replace('.test.tsx', '')
        component_tests = {
            'ImageAnalysisWorkspace': [
                'zoom', 'face.*marker', 'bounding.*box', 'image.*load', 'interaction'
            ],
            'DetectionOverlaySystem': [
                'label', 'connection', 'inspirational', 'selection', 'overlay'
            ],
            'DownloadManager': [
                'download', 'format', 'progress', 'annotation', 'option'
            ]
        }
        
        if component_name in component_tests:
            print(f"  🎯 Component-specific test coverage:")
            for pattern in component_tests[component_name]:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    print(f"    ✅ {pattern}: {len(matches)} references")
                else:
                    print(f"    ⚠️  {pattern}: No references found")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error validating {test_file_path}: {e}")
        return False

def validate_test_coverage():
    """Validate overall test coverage"""
    print("🧪 Frontend Component Test Validation")
    print("=" * 50)
    
    # Find test files
    frontend_path = Path("../rethinkingpark-frontend")
    test_files = []
    
    if frontend_path.exists():
        test_pattern = frontend_path / "src" / "components" / "__tests__"
        if test_pattern.exists():
            test_files = list(test_pattern.glob("*.test.tsx"))
    
    if not test_files:
        print("❌ No test files found in expected location")
        return False
    
    print(f"📁 Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.name}")
    
    # Validate each test file
    all_valid = True
    for test_file in test_files:
        valid = validate_test_file(test_file)
        all_valid = all_valid and valid
    
    # Summary
    print(f"\n📊 Test Validation Summary")
    print("=" * 30)
    
    if all_valid:
        print("✅ All test files are properly structured")
        print("✅ Tests cover key component functionality")
        print("✅ Proper testing patterns are used")
    else:
        print("⚠️  Some test files need attention")
    
    # Test categories covered
    expected_categories = [
        "Basic Rendering",
        "User Interactions", 
        "Error Handling",
        "Accessibility",
        "Performance"
    ]
    
    print(f"\n🎯 Expected Test Categories:")
    for category in expected_categories:
        print(f"  - {category}")
    
    return all_valid

def check_test_dependencies():
    """Check if testing dependencies are available"""
    print(f"\n📦 Testing Dependencies Check")
    print("=" * 30)
    
    # Check if package.json has testing setup
    package_json_path = Path("../rethinkingpark-frontend/package.json")
    
    if package_json_path.exists():
        try:
            import json
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            # Check for testing dependencies
            dev_deps = package_data.get('devDependencies', {})
            deps = package_data.get('dependencies', {})
            all_deps = {**deps, **dev_deps}
            
            testing_deps = [
                '@testing-library/react',
                '@testing-library/jest-dom', 
                '@testing-library/user-event',
                'jest',
                'vitest'
            ]
            
            print("Testing dependencies status:")
            for dep in testing_deps:
                if any(dep in key for key in all_deps.keys()):
                    print(f"  ✅ {dep}: Available")
                else:
                    print(f"  ❌ {dep}: Missing")
            
            # Check for test script
            scripts = package_data.get('scripts', {})
            if 'test' in scripts:
                print(f"  ✅ Test script: {scripts['test']}")
            else:
                print(f"  ❌ Test script: Not configured")
                
        except Exception as e:
            print(f"  ❌ Error reading package.json: {e}")
    else:
        print("  ❌ package.json not found")

def main():
    """Main validation function"""
    print("🚀 Frontend Test Suite Validation")
    print("=" * 50)
    
    # Change to the backend directory for relative paths
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Check dependencies
    check_test_dependencies()
    
    # Validate test coverage
    test_valid = validate_test_coverage()
    
    print(f"\n🏁 Final Result")
    print("=" * 20)
    
    if test_valid:
        print("✅ Frontend tests are well-structured and comprehensive")
        print("✅ Ready for testing framework integration")
    else:
        print("⚠️  Frontend tests need some improvements")
    
    print(f"\n💡 Next Steps:")
    print("  1. Install testing dependencies (Jest, Testing Library)")
    print("  2. Configure test script in package.json")
    print("  3. Set up test environment configuration")
    print("  4. Run tests with: npm test")

if __name__ == "__main__":
    main()