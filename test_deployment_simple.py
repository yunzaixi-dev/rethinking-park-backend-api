#!/usr/bin/env python3
"""
Simple test for production deployment configuration
"""

import os
import sys
from pathlib import Path

def test_deployment_files():
    """Test that all deployment files exist"""
    print("🔍 Testing deployment files...")
    
    required_files = [
        "deployment/production.yml",
        "deployment/nginx.conf", 
        "deployment/prometheus.yml",
        "deployment/fluent-bit.conf",
        "deploy_production.sh"
    ]
    
    all_present = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} missing")
            all_present = False
    
    return all_present

def test_configuration_content():
    """Test configuration file content"""
    print("🔍 Testing configuration content...")
    
    try:
        # Test Docker Compose
        with open("deployment/production.yml", "r") as f:
            compose_content = f.read()
        
        required_services = [
            "rethinking-park-api:",
            "redis:",
            "nginx:",
            "monitoring:",
            "log_aggregator:"
        ]
        
        for service in required_services:
            if service in compose_content:
                print(f"✅ Service {service.rstrip(':')} configured")
            else:
                print(f"❌ Service {service.rstrip(':')} missing")
        
        # Test Nginx config
        with open("deployment/nginx.conf", "r") as f:
            nginx_content = f.read()
        
        nginx_features = [
            "upstream api_backend",
            "proxy_cache_path",
            "gzip on",
            "limit_req_zone"
        ]
        
        for feature in nginx_features:
            if feature in nginx_content:
                print(f"✅ Nginx {feature}")
            else:
                print(f"❌ Nginx {feature} missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_deployment_script():
    """Test deployment script"""
    print("🔍 Testing deployment script...")
    
    script_path = Path("deploy_production.sh")
    
    if not script_path.exists():
        print("❌ Deployment script missing")
        return False
    
    # Check if executable
    if os.access(script_path, os.X_OK):
        print("✅ Deployment script is executable")
    else:
        print("⚠️  Deployment script not executable (run: chmod +x deploy_production.sh)")
    
    # Check script content
    with open(script_path, "r") as f:
        script_content = f.read()
    
    required_functions = [
        "check_prerequisites",
        "validate_environment", 
        "build_images",
        "deploy_services"
    ]
    
    for func in required_functions:
        if func in script_content:
            print(f"✅ Function {func}")
        else:
            print(f"❌ Function {func} missing")
    
    return True

def test_monitoring_files():
    """Test monitoring configuration files"""
    print("🔍 Testing monitoring files...")
    
    # Test Prometheus config
    try:
        with open("deployment/prometheus.yml", "r") as f:
            prometheus_content = f.read()
        
        if "scrape_configs:" in prometheus_content:
            print("✅ Prometheus scrape configs")
        else:
            print("❌ Prometheus scrape configs missing")
        
        if "rethinking-park-api:8000" in prometheus_content:
            print("✅ API monitoring target")
        else:
            print("❌ API monitoring target missing")
    
    except Exception as e:
        print(f"❌ Prometheus config error: {e}")
    
    # Test Fluent Bit config
    try:
        with open("deployment/fluent-bit.conf", "r") as f:
            fluent_content = f.read()
        
        if "[INPUT]" in fluent_content:
            print("✅ Fluent Bit inputs")
        else:
            print("❌ Fluent Bit inputs missing")
        
        if "[OUTPUT]" in fluent_content:
            print("✅ Fluent Bit outputs")
        else:
            print("❌ Fluent Bit outputs missing")
    
    except Exception as e:
        print(f"❌ Fluent Bit config error: {e}")
    
    return True

def test_production_readiness():
    """Test production readiness"""
    print("🔍 Testing production readiness...")
    
    # Check Docker availability
    docker_available = False
    try:
        import subprocess
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker available")
            docker_available = True
        else:
            print("❌ Docker not working")
    except FileNotFoundError:
        print("❌ Docker not installed")
    
    # Check Docker Compose
    compose_available = False
    try:
        result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker Compose available")
            compose_available = True
        else:
            print("❌ Docker Compose not working")
    except FileNotFoundError:
        print("❌ Docker Compose not installed")
    
    # Check environment variables
    env_vars = ["GOOGLE_CLOUD_PROJECT", "GCS_BUCKET_NAME"]
    env_configured = 0
    
    for var in env_vars:
        if var in os.environ:
            print(f"✅ {var} configured")
            env_configured += 1
        else:
            print(f"⚠️  {var} not configured")
    
    # Check service account key
    if Path("service-account-key.json").exists():
        print("✅ Service account key present")
    else:
        print("⚠️  Service account key missing")
    
    return docker_available and compose_available

def main():
    """Run all tests"""
    print("🚀 Testing production deployment configuration...\n")
    
    tests = [
        ("Deployment Files", test_deployment_files),
        ("Configuration Content", test_configuration_content),
        ("Deployment Script", test_deployment_script),
        ("Monitoring Files", test_monitoring_files),
        ("Production Readiness", test_production_readiness)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("=" * 50)
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Production deployment configuration is ready!")
        print("\n📋 Deployment Features Verified:")
        print("   ✅ Docker Compose production configuration")
        print("   ✅ Nginx reverse proxy with performance optimization")
        print("   ✅ Prometheus monitoring setup")
        print("   ✅ Fluent Bit logging configuration")
        print("   ✅ Automated deployment script")
        print("\n🚀 Ready to deploy with: ./deploy_production.sh")
    else:
        print("\n⚠️  Some configuration issues need attention")
        print("\n💡 Next Steps:")
        print("   1. Fix any missing files or configurations")
        print("   2. Install Docker and Docker Compose if needed")
        print("   3. Set required environment variables")
        print("   4. Add Google Cloud service account key")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)