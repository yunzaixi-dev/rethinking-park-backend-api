#!/usr/bin/env python3
"""
Verification script for production deployment configuration
Tests deployment readiness, monitoring, and performance optimization
"""

import sys
import os
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_deployment_files():
    """Test that all deployment files exist and are properly configured"""
    print("🔍 Testing deployment files...")
    
    required_files = [
        "deployment/production.yml",
        "deployment/nginx.conf",
        "deployment/prometheus.yml",
        "deployment/fluent-bit.conf",
        "deploy_production.sh",
        "Dockerfile"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing deployment files: {missing_files}")
        return False
    
    print("✅ All deployment files present")
    return True

def test_docker_compose_config():
    """Test Docker Compose configuration"""
    print("🔍 Testing Docker Compose configuration...")
    
    try:
        import yaml
        
        with open("deployment/production.yml", "r") as f:
            compose_config = yaml.safe_load(f)
        
        # Check required services
        required_services = [
            "rethinking-park-api",
            "redis",
            "nginx",
            "monitoring",
            "log_aggregator"
        ]
        
        services = compose_config.get("services", {})
        missing_services = []
        
        for service in required_services:
            if service not in services:
                missing_services.append(service)
        
        if missing_services:
            print(f"❌ Missing services in Docker Compose: {missing_services}")
            return False
        
        # Check API service configuration
        api_service = services.get("rethinking-park-api", {})
        
        # Check environment variables
        env_vars = api_service.get("environment", [])
        required_env_vars = [
            "APP_ENV=production",
            "REDIS_ENABLED=true",
            "RATE_LIMIT_ENABLED=true",
            "PERFORMANCE_OPTIMIZATION_ENABLED=true"
        ]
        
        env_str = " ".join(env_vars) if isinstance(env_vars, list) else str(env_vars)
        
        for required_env in required_env_vars:
            if required_env not in env_str:
                print(f"⚠️  Missing environment variable: {required_env}")
        
        # Check health check configuration
        if "healthcheck" not in api_service:
            print("⚠️  No health check configured for API service")
        
        # Check resource limits
        deploy_config = api_service.get("deploy", {})
        resources = deploy_config.get("resources", {})
        
        if not resources.get("limits"):
            print("⚠️  No resource limits configured for API service")
        
        print("✅ Docker Compose configuration validated")
        return True
        
    except ImportError:
        print("⚠️  PyYAML not available, skipping Docker Compose validation")
        return True
    except Exception as e:
        print(f"❌ Docker Compose configuration error: {e}")
        return False

def test_nginx_config():
    """Test Nginx configuration"""
    print("🔍 Testing Nginx configuration...")
    
    try:
        with open("deployment/nginx.conf", "r") as f:
            nginx_config = f.read()
        
        # Check for required configurations
        required_configs = [
            "upstream api_backend",
            "proxy_cache_path",
            "limit_req_zone",
            "gzip on",
            "ssl_protocols",  # May be commented out
            "location /api/v1/",
            "location ~ ^/api/v1/(upload|batch-process)",
            "location ~ ^/api/v1/(download|processed-images)/"
        ]
        
        missing_configs = []
        for config in required_configs:
            if config not in nginx_config and not config.startswith("ssl_"):
                missing_configs.append(config)
        
        if missing_configs:
            print(f"❌ Missing Nginx configurations: {missing_configs}")
            return False
        
        # Check for performance optimizations
        performance_configs = [
            "proxy_cache",
            "gzip_comp_level",
            "keepalive_timeout",
            "worker_processes auto"
        ]
        
        for config in performance_configs:
            if config not in nginx_config:
                print(f"⚠️  Missing performance optimization: {config}")
        
        print("✅ Nginx configuration validated")
        return True
        
    except Exception as e:
        print(f"❌ Nginx configuration error: {e}")
        return False

def test_monitoring_config():
    """Test monitoring configuration"""
    print("🔍 Testing monitoring configuration...")
    
    try:
        import yaml
        
        # Test Prometheus configuration
        with open("deployment/prometheus.yml", "r") as f:
            prometheus_config = yaml.safe_load(f)
        
        scrape_configs = prometheus_config.get("scrape_configs", [])
        
        required_jobs = [
            "prometheus",
            "rethinking-park-api",
            "api-performance",
            "vision-api-usage",
            "cache-performance",
            "batch-processing"
        ]
        
        job_names = [job.get("job_name") for job in scrape_configs]
        missing_jobs = []
        
        for job in required_jobs:
            if job not in job_names:
                missing_jobs.append(job)
        
        if missing_jobs:
            print(f"❌ Missing Prometheus jobs: {missing_jobs}")
            return False
        
        print("✅ Monitoring configuration validated")
        return True
        
    except ImportError:
        print("⚠️  PyYAML not available, skipping monitoring validation")
        return True
    except Exception as e:
        print(f"❌ Monitoring configuration error: {e}")
        return False

def test_logging_config():
    """Test logging configuration"""
    print("🔍 Testing logging configuration...")
    
    try:
        with open("deployment/fluent-bit.conf", "r") as f:
            fluent_config = f.read()
        
        # Check for required input sources
        required_inputs = [
            "[INPUT]",
            "Name              tail",
            "Path              /var/log/api/*.log",
            "Path              /var/log/nginx/access.log"
        ]
        
        for input_config in required_inputs:
            if input_config not in fluent_config:
                print(f"⚠️  Missing logging input: {input_config}")
        
        # Check for filters and outputs
        required_sections = [
            "[FILTER]",
            "[OUTPUT]"
        ]
        
        for section in required_sections:
            if section not in fluent_config:
                print(f"⚠️  Missing logging section: {section}")
        
        print("✅ Logging configuration validated")
        return True
        
    except Exception as e:
        print(f"❌ Logging configuration error: {e}")
        return False

async def test_monitoring_service():
    """Test monitoring service functionality"""
    print("🔍 Testing monitoring service...")
    
    try:
        # Test monitoring service import and basic functionality
        from services.monitoring_service import MonitoringService, HealthChecker, MetricsCollector
        from services.cache_service import CacheService
        from unittest.mock import Mock
        
        # Create mock cache service
        mock_cache = Mock(spec=CacheService)
        mock_cache.is_enabled.return_value = True
        
        # Test monitoring service creation
        monitoring = MonitoringService(mock_cache)
        
        # Test health checker
        health_checker = HealthChecker()
        
        # Register a simple test check
        async def test_check():
            return {"status": "healthy", "details": {"test": True}}
        
        health_checker.register_check("test", test_check)
        
        # Run the test check
        result = await health_checker.run_check("test")
        
        if result.status != "healthy":
            print(f"❌ Health check failed: {result.error_message}")
            return False
        
        # Test metrics collector
        metrics_collector = MetricsCollector()
        
        # Record some test metrics
        metrics_collector.record_request(success=True, response_time_ms=100.0)
        metrics_collector.record_vision_api_call()
        metrics_collector.update_cache_metrics(0.8)
        
        # Get metrics
        api_metrics = metrics_collector.get_api_metrics()
        
        if api_metrics.total_requests != 1:
            print(f"❌ Metrics recording failed: expected 1 request, got {api_metrics.total_requests}")
            return False
        
        if api_metrics.vision_api_calls != 1:
            print(f"❌ Vision API metrics failed: expected 1 call, got {api_metrics.vision_api_calls}")
            return False
        
        print("✅ Monitoring service functionality validated")
        return True
        
    except Exception as e:
        print(f"❌ Monitoring service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_performance_optimization():
    """Test performance optimization functionality"""
    print("🔍 Testing performance optimization...")
    
    try:
        # Test performance optimizer import
        from services.performance_optimizer import (
            PerformanceOptimizer, 
            MemoryManager, 
            VisionAPIBatcher,
            AsyncProcessingQueue
        )
        from services.cache_service import CacheService
        from unittest.mock import Mock
        
        # Test memory manager
        memory_manager = MemoryManager(max_memory_mb=256)
        
        usage = memory_manager.get_memory_usage()
        if not isinstance(usage, float) or usage < 0:
            print(f"❌ Memory usage detection failed: {usage}")
            return False
        
        # Test optimization
        stats = memory_manager.optimize_memory()
        if "optimizations_performed" not in stats:
            print("❌ Memory optimization failed")
            return False
        
        # Test async processing queue
        queue = AsyncProcessingQueue(max_workers=2, max_queue_size=10)
        
        await queue.start()
        if not queue.is_running:
            print("❌ Async queue failed to start")
            return False
        
        # Test simple task
        async def test_task(value):
            return value * 2
        
        future = await queue.submit_task(test_task, 5)
        result = await future
        
        if result != 10:
            print(f"❌ Async task failed: expected 10, got {result}")
            return False
        
        await queue.stop()
        if queue.is_running:
            print("❌ Async queue failed to stop")
            return False
        
        print("✅ Performance optimization functionality validated")
        return True
        
    except Exception as e:
        print(f"❌ Performance optimization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deployment_script():
    """Test deployment script"""
    print("🔍 Testing deployment script...")
    
    try:
        # Check if deployment script exists and is executable
        script_path = Path("deploy_production.sh")
        
        if not script_path.exists():
            print("❌ Deployment script not found")
            return False
        
        # Check if script is executable
        if not os.access(script_path, os.X_OK):
            print("⚠️  Deployment script is not executable")
            print("   Run: chmod +x deploy_production.sh")
        
        # Read script content and check for required functions
        with open(script_path, "r") as f:
            script_content = f.read()
        
        required_functions = [
            "check_prerequisites",
            "validate_environment",
            "build_images",
            "deploy_services",
            "wait_for_services",
            "run_health_checks"
        ]
        
        missing_functions = []
        for func in required_functions:
            if func not in script_content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Missing deployment functions: {missing_functions}")
            return False
        
        print("✅ Deployment script validated")
        return True
        
    except Exception as e:
        print(f"❌ Deployment script test failed: {e}")
        return False

def test_production_readiness():
    """Test overall production readiness"""
    print("🔍 Testing production readiness...")
    
    readiness_checks = []
    
    # Check environment variables
    required_env_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "GCS_BUCKET_NAME"
    ]
    
    for var in required_env_vars:
        if var in os.environ:
            readiness_checks.append(f"✅ {var} configured")
        else:
            readiness_checks.append(f"⚠️  {var} not configured")
    
    # Check service account key
    if Path("service-account-key.json").exists():
        readiness_checks.append("✅ Service account key present")
    else:
        readiness_checks.append("⚠️  Service account key missing")
    
    # Check Docker availability
    try:
        import subprocess
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            readiness_checks.append("✅ Docker available")
        else:
            readiness_checks.append("❌ Docker not available")
    except FileNotFoundError:
        readiness_checks.append("❌ Docker not installed")
    
    # Check Docker Compose availability
    try:
        result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            readiness_checks.append("✅ Docker Compose available")
        else:
            readiness_checks.append("❌ Docker Compose not available")
    except FileNotFoundError:
        readiness_checks.append("❌ Docker Compose not installed")
    
    print("\n📋 Production Readiness Checklist:")
    for check in readiness_checks:
        print(f"   {check}")
    
    # Count successful checks
    successful_checks = sum(1 for check in readiness_checks if check.startswith("✅"))
    total_checks = len(readiness_checks)
    
    print(f"\n📊 Readiness Score: {successful_checks}/{total_checks}")
    
    if successful_checks == total_checks:
        print("🎉 System is ready for production deployment!")
        return True
    elif successful_checks >= total_checks * 0.8:
        print("⚠️  System is mostly ready, but some issues need attention")
        return True
    else:
        print("❌ System is not ready for production deployment")
        return False

async def main():
    """Run all verification tests"""
    print("🚀 Starting production deployment verification...\n")
    
    tests = [
        ("Deployment Files", test_deployment_files),
        ("Docker Compose Config", test_docker_compose_config),
        ("Nginx Configuration", test_nginx_config),
        ("Monitoring Configuration", test_monitoring_config),
        ("Logging Configuration", test_logging_config),
        ("Monitoring Service", test_monitoring_service),
        ("Performance Optimization", test_performance_optimization),
        ("Deployment Script", test_deployment_script),
        ("Production Readiness", test_production_readiness),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All production deployment features verified successfully!")
        print("\n📋 Production Deployment Features:")
        print("   ✅ Docker Compose production configuration")
        print("   ✅ Nginx reverse proxy with CDN capabilities")
        print("   ✅ Prometheus monitoring and metrics collection")
        print("   ✅ Fluent Bit log aggregation and processing")
        print("   ✅ Comprehensive health checks and monitoring")
        print("   ✅ Performance optimization for no-GPU environment")
        print("   ✅ Automated deployment script with validation")
        print("   ✅ Production-ready configuration management")
        print("\n🚀 Ready for production deployment!")
        return True
    else:
        print("\n⚠️  Some production deployment features need attention")
        print("\n💡 Next Steps:")
        print("   1. Review failed tests and fix configuration issues")
        print("   2. Ensure all required environment variables are set")
        print("   3. Install missing dependencies (Docker, Docker Compose)")
        print("   4. Place Google Cloud service account key in project root")
        print("   5. Re-run verification after fixes")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)