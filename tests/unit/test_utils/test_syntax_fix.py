#!/usr/bin/env python3
"""
简单的语法修复验证脚本
"""

import ast
import sys


def test_syntax():
    """测试main.py的语法是否正确"""
    print("🔍 检查main.py语法...")

    try:
        with open("main.py", "r", encoding="utf-8") as f:
            source_code = f.read()

        # 尝试解析AST
        ast.parse(source_code)
        print("✅ main.py 语法检查通过")
        return True

    except SyntaxError as e:
        print(f"❌ 语法错误在第 {e.lineno} 行: {e.msg}")
        print(f"   错误内容: {e.text}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False


def test_import():
    """测试基本导入"""
    print("🔍 测试基本导入...")

    try:
        # 测试导入main模块
        import main

        print("✅ main模块导入成功")

        # 检查app对象是否存在
        if hasattr(main, "app"):
            print("✅ FastAPI app对象存在")
            return True
        else:
            print("❌ 找不到FastAPI app对象")
            return False

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False


def main_test():
    """主测试函数"""
    print("🚀 开始语法修复验证")
    print("=" * 40)

    # 测试语法
    syntax_ok = test_syntax()
    if not syntax_ok:
        print("❌ 语法测试失败")
        return False

    # 测试导入
    import_ok = test_import()
    if not import_ok:
        print("❌ 导入测试失败")
        return False

    print("=" * 40)
    print("🎉 所有测试通过！")
    print("💡 缩进错误已修复，可以重新部署")
    return True


if __name__ == "__main__":
    success = main_test()
    sys.exit(0 if success else 1)
