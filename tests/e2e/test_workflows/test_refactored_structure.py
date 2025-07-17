#!/usr/bin/env python3
"""
测试重构后的应用结构
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """测试所有重要的导入"""
    try:
        print("Testing imports...")

        # 测试核心模块导入
        from app.main import app

        print("✅ App main module imported successfully")

        from app.core.middleware import setup_middleware

        print("✅ Middleware module imported successfully")

        from app.core.exceptions import setup_exception_handlers

        print("✅ Exceptions module imported successfully")

        # 测试API路由导入
        from app.api.v1.router import api_router

        print("✅ API router imported successfully")

        from app.api.v1.endpoints import admin, analysis, batch, health, images

        print("✅ All endpoint modules imported successfully")

        # 测试配置导入
        from app.config.settings import settings

        print("✅ Settings imported successfully")

        print(
            "\n🎉 All imports successful! The refactored structure is working correctly."
        )
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_app_creation():
    """测试应用创建"""
    try:
        from app.main import create_application

        # 创建应用实例
        test_app = create_application()
        print("✅ Application created successfully")

        # 检查应用属性
        if hasattr(test_app, "title"):
            print(f"✅ App title: {test_app.title}")

        if hasattr(test_app, "version"):
            print(f"✅ App version: {test_app.version}")

        return True

    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 50)
    print("Testing Refactored Backend Structure")
    print("=" * 50)

    # 测试导入
    imports_ok = test_imports()

    print("\n" + "=" * 50)

    # 测试应用创建
    if imports_ok:
        app_ok = test_app_creation()
    else:
        app_ok = False

    print("\n" + "=" * 50)

    if imports_ok and app_ok:
        print("🎉 All tests passed! The refactored structure is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
