#!/usr/bin/env python3
"""
配置系统测试脚本

验证新的配置管理系统是否正常工作。
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_config_modules():
    """测试配置模块导入"""
    print("Testing configuration module imports...")

    try:
        from app.config.app import AppConfig
        from app.config.base import BaseConfig, ConfigValidationError
        from app.config.cache import CacheConfig
        from app.config.database import DatabaseConfig
        from app.config.external import ExternalServicesConfig
        from app.config.loader import ConfigLoader, config_loader

        print("✓ All configuration modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import configuration modules: {e}")
        return False


def test_config_classes():
    """测试配置类实例化"""
    print("\nTesting configuration class instantiation...")

    try:
        from app.config.app import AppConfig
        from app.config.cache import CacheConfig
        from app.config.database import DatabaseConfig
        from app.config.external import ExternalServicesConfig

        # 测试各个配置类
        app_config = AppConfig()
        print(f"✓ AppConfig: {app_config.APP_NAME} v{app_config.APP_VERSION}")

        db_config = DatabaseConfig()
        print(f"✓ DatabaseConfig: {db_config.DATABASE_HOST}:{db_config.DATABASE_PORT}")

        cache_config = CacheConfig()
        print(f"✓ CacheConfig: Redis enabled={cache_config.REDIS_ENABLED}")

        external_config = ExternalServicesConfig()
        print(
            f"✓ ExternalServicesConfig: Monitoring enabled={external_config.MONITORING_ENABLED}"
        )

        return True
    except Exception as e:
        print(f"✗ Failed to instantiate configuration classes: {e}")
        return False


def test_config_validation():
    """测试配置验证"""
    print("\nTesting configuration validation...")

    try:
        from app.config.app import AppConfig
        from app.config.base import ConfigValidationError

        # 测试正常配置
        config = AppConfig()
        config.validate_config()
        print("✓ Valid configuration passed validation")

        # 测试无效配置
        config.APP_NAME = ""
        try:
            config.validate_config()
            print("✗ Invalid configuration should have failed validation")
            return False
        except ConfigValidationError:
            print("✓ Invalid configuration correctly failed validation")

        return True
    except Exception as e:
        print(f"✗ Configuration validation test failed: {e}")
        return False


def test_config_loader():
    """测试配置加载器"""
    print("\nTesting configuration loader...")

    try:
        from app.config.loader import ConfigLoader

        # 创建临时配置目录
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = ConfigLoader(temp_dir)

            # 测试环境验证
            assert loader.validate_environment("development")
            assert loader.validate_environment("production")
            assert not loader.validate_environment("invalid")
            print("✓ Environment validation works correctly")

            # 测试可用环境列表
            environments = loader.get_available_environments()
            assert "development" in environments
            assert "production" in environments
            print(f"✓ Available environments: {environments}")

        return True
    except Exception as e:
        print(f"✗ Configuration loader test failed: {e}")
        return False


def test_unified_settings():
    """测试统一配置"""
    print("\nTesting unified settings...")

    try:
        # 设置测试环境变量
        os.environ["ENVIRONMENT"] = "development"
        os.environ["APP_NAME"] = "Test App"
        os.environ["DEBUG"] = "true"

        from app.config.settings import Settings

        settings = Settings()

        # 测试配置访问
        print(f"✓ App name: {settings.app.APP_NAME}")
        print(f"✓ Debug mode: {settings.app.DEBUG}")
        print(f"✓ Environment: {settings.app.ENVIRONMENT}")

        # 测试向后兼容属性
        print(f"✓ Backward compatible APP_NAME: {settings.APP_NAME}")
        print(f"✓ Backward compatible DEBUG: {settings.DEBUG}")

        # 测试配置字典转换
        config_dict = settings.to_dict()
        assert "app" in config_dict
        assert "database" in config_dict
        assert "cache" in config_dict
        assert "external" in config_dict
        print("✓ Configuration dictionary conversion works")

        return True
    except Exception as e:
        print(f"✗ Unified settings test failed: {e}")
        return False


def test_environment_files():
    """测试环境配置文件"""
    print("\nTesting environment configuration files...")

    config_dir = project_root / "config"

    # 检查配置文件是否存在
    env_files = ["local.env", "staging.env", "production.env"]

    for env_file in env_files:
        file_path = config_dir / env_file
        if file_path.exists():
            print(f"✓ {env_file} exists")
        else:
            print(f"✗ {env_file} not found")
            return False

    # 检查示例配置文件
    example_file = project_root / ".env.example"
    if example_file.exists():
        print("✓ .env.example exists")
    else:
        print("✗ .env.example not found")
        return False

    return True


def test_documentation():
    """测试文档文件"""
    print("\nTesting documentation files...")

    docs_dir = project_root / "docs"
    config_doc = docs_dir / "configuration.md"

    if config_doc.exists():
        print("✓ Configuration documentation exists")
        return True
    else:
        print("✗ Configuration documentation not found")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Configuration System Test Suite")
    print("=" * 60)

    tests = [
        test_config_modules,
        test_config_classes,
        test_config_validation,
        test_config_loader,
        test_unified_settings,
        test_environment_files,
        test_documentation,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")

    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 All tests passed! Configuration system is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the configuration system.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
