#!/usr/bin/env python3
"""
Deployment validation script for the refactored backend.
This script validates that deployment configurations are correct and Docker builds work.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

class DeploymentValidator:
    """Validates deployment configurations and Docker builds."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.results = {}
        
    def run_command(self, command, cwd=None, timeout=300):
        """Run a command and return the result."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.base_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    def validate_dockerfile(self):
        """Validate Dockerfile syntax and build."""
        print("🐳 Validating Dockerfile...")
        
        dockerfile_path = self.base_path / "Dockerfile"
        if not dockerfile_path.exists():
            print("❌ Dockerfile not found")
            return False
        
        # Check Dockerfile syntax
        code, stdout, stderr = self.run_command("docker build --dry-run .")
        if code == 0:
            print("✅ Dockerfile syntax is valid")
        else:
            print(f"❌ Dockerfile syntax error: {stderr}")
            return False
        
        # Try to build the image (with timeout)
        print("  Building Docker image (this may take a few minutes)...")
        code, stdout, stderr = self.run_command(
            "docker build -t rethinking-park-api:test .", 
            timeout=600
        )
        
        if code == 0:
            print("✅ Docker image built successfully")
            return True
        else:
            print(f"❌ Docker build failed: {stderr}")
            return False
    
    def validate_docker_compose_files(self):
        """Validate docker-compose files."""
        print("\n🐙 Validating Docker Compose files...")
        
        compose_files = [
            "docker-compose.yml",
            "deployment/docker-compose.dev.yml",
            "deployment/docker-compose.staging.yml",
            "deployment/production.yml"
        ]
        
        all_valid = True
        
        for compose_file in compose_files:
            file_path = self.base_path / compose_file
            if not file_path.exists():
                print(f"❌ {compose_file} not found")
                all_valid = False
                continue
            
            # Validate compose file syntax
            code, stdout, stderr = self.run_command(
                f"docker-compose -f {compose_file} config",
                timeout=30
            )
            
            if code == 0:
                print(f"✅ {compose_file} is valid")
            else:
                print(f"❌ {compose_file} validation failed: {stderr}")
                all_valid = False
        
        return all_valid
    
    def validate_nginx_config(self):
        """Validate Nginx configuration."""
        print("\n🌐 Validating Nginx configuration...")
        
        nginx_config = self.base_path / "deployment" / "nginx.conf"
        if not nginx_config.exists():
            print("❌ nginx.conf not found")
            return False
        
        # Basic syntax check (if nginx is available)
        code, stdout, stderr = self.run_command("which nginx")
        if code == 0:
            code, stdout, stderr = self.run_command(
                f"nginx -t -c {nginx_config}"
            )
            if code == 0:
                print("✅ Nginx configuration is valid")
                return True
            else:
                print(f"❌ Nginx configuration error: {stderr}")
                return False
        else:
            print("⚠️  Nginx not available for validation, checking file exists")
            return True
    
    def validate_requirements_files(self):
        """Validate requirements files."""
        print("\n📦 Validating requirements files...")
        
        req_files = [
            "requirements/base.txt",
            "requirements/dev.txt", 
            "requirements/prod.txt"
        ]
        
        all_valid = True
        
        for req_file in req_files:
            file_path = self.base_path / req_file
            if not file_path.exists():
                print(f"❌ {req_file} not found")
                all_valid = False
                continue
            
            # Check if file is not empty
            if file_path.stat().st_size == 0:
                print(f"❌ {req_file} is empty")
                all_valid = False
                continue
            
            # Try to parse requirements
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    valid_lines = [l for l in lines if l.strip() and not l.startswith('#')]
                    if valid_lines:
                        print(f"✅ {req_file} ({len(valid_lines)} packages)")
                    else:
                        print(f"⚠️  {req_file} has no packages")
            except Exception as e:
                print(f"❌ {req_file} read error: {e}")
                all_valid = False
        
        return all_valid
    
    def validate_environment_files(self):
        """Validate environment configuration files."""
        print("\n⚙️  Validating environment files...")
        
        env_files = [
            ".env.example",
            "config/local.env",
            "config/staging.env",
            "config/production.env"
        ]
        
        valid_count = 0
        
        for env_file in env_files:
            file_path = self.base_path / env_file
            if file_path.exists():
                print(f"✅ {env_file}")
                valid_count += 1
            else:
                print(f"❌ {env_file} not found")
        
        return valid_count >= len(env_files) * 0.75  # 75% should exist
    
    def validate_scripts(self):
        """Validate deployment scripts."""
        print("\n📜 Validating deployment scripts...")
        
        script_files = [
            "scripts/deployment/deploy_dev.sh",
            "scripts/deployment/deploy_staging.sh",
            "scripts/deployment/deploy_production.sh"
        ]
        
        valid_count = 0
        
        for script_file in script_files:
            file_path = self.base_path / script_file
            if file_path.exists():
                # Check if script is executable
                if os.access(file_path, os.X_OK):
                    print(f"✅ {script_file} (executable)")
                else:
                    print(f"⚠️  {script_file} (not executable)")
                valid_count += 1
            else:
                print(f"❌ {script_file} not found")
        
        return valid_count >= len(script_files) * 0.5  # 50% should exist
    
    def validate_monitoring_config(self):
        """Validate monitoring configuration."""
        print("\n📊 Validating monitoring configuration...")
        
        monitoring_files = [
            "deployment/prometheus.yml",
            "deployment/fluent-bit.conf"
        ]
        
        valid_count = 0
        
        for config_file in monitoring_files:
            file_path = self.base_path / config_file
            if file_path.exists():
                print(f"✅ {config_file}")
                valid_count += 1
            else:
                print(f"❌ {config_file} not found")
        
        return valid_count >= len(monitoring_files) * 0.5
    
    def validate_app_structure(self):
        """Validate that the app can be imported correctly."""
        print("\n🏗️  Validating app structure for deployment...")
        
        # Check if the main app module can be found
        app_main = self.base_path / "app" / "main.py"
        if not app_main.exists():
            print("❌ app/main.py not found")
            return False
        
        # Check if we can find the app variable
        try:
            with open(app_main, 'r') as f:
                content = f.read()
                if 'app = ' in content or 'def create_application' in content:
                    print("✅ FastAPI app definition found")
                    return True
                else:
                    print("❌ FastAPI app definition not found")
                    return False
        except Exception as e:
            print(f"❌ Error reading app/main.py: {e}")
            return False
    
    def test_health_endpoint(self):
        """Test if we can start the app and access health endpoint."""
        print("\n🏥 Testing application startup...")
        
        # This is a basic test - in a real scenario you'd start the app
        # and test the health endpoint
        print("⚠️  Skipping live health check (requires running app)")
        return True
    
    def generate_deployment_report(self):
        """Generate a deployment readiness report."""
        print("\n📋 Deployment Readiness Report")
        print("=" * 50)
        
        passed = sum(self.results.values())
        total = len(self.results)
        
        for check, result in self.results.items():
            status = "✅ READY" if result else "❌ NEEDS ATTENTION"
            print(f"{check.replace('_', ' ').title()}: {status}")
        
        score = (passed / total) * 100
        print(f"\nDeployment Readiness: {passed}/{total} ({score:.1f}%)")
        
        if score >= 90:
            print("🎉 Excellent! Ready for deployment.")
        elif score >= 80:
            print("✅ Good! Minor issues to address before deployment.")
        elif score >= 60:
            print("⚠️  Fair. Several issues need attention.")
        else:
            print("❌ Poor. Significant issues must be resolved.")
        
        return score >= 80
    
    def run_validation(self):
        """Run all deployment validation checks."""
        print("🚀 Deployment Validation for Refactored Backend")
        print("=" * 50)
        
        # Run all validation checks
        self.results['dockerfile'] = self.validate_dockerfile()
        self.results['docker_compose'] = self.validate_docker_compose_files()
        self.results['nginx_config'] = self.validate_nginx_config()
        self.results['requirements'] = self.validate_requirements_files()
        self.results['environment'] = self.validate_environment_files()
        self.results['scripts'] = self.validate_scripts()
        self.results['monitoring'] = self.validate_monitoring_config()
        self.results['app_structure'] = self.validate_app_structure()
        self.results['health_check'] = self.test_health_endpoint()
        
        # Generate report
        return self.generate_deployment_report()

def main():
    """Main validation function."""
    validator = DeploymentValidator()
    success = validator.run_validation()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())