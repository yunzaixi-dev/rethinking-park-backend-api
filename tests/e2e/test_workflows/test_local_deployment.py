#!/usr/bin/env python3
"""
本地部署测试脚本
测试修复后的main.py是否能正常启动
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def test_python_syntax():
    """测试Python语法是否正确"""
    print("🔍 检查Python语法...")

    try:
        # 检查main.py语法
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "main.py"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ main.py 语法检查通过")
            return True
        else:
            print(f"❌ main.py 语法错误:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 语法检查失败: {e}")
        return False


def test_imports():
    """测试导入是否正常"""
    print("🔍 检查模块导入...")

    test_script = """
import sys
sys.path.append('.')

try:
    from main import app
    print("✅ 主应用导入成功")
    
    # 检查关键组件
    from config import settings
    print("✅ 配置导入成功")
    
    from services.gcs_service import gcs_service
    print("✅ GCS服务导入成功")
    
    from services.vision_service import vision_service
    print("✅ Vision服务导入成功")
    
    print("✅ 所有核心模块导入成功")
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 其他错误: {e}")
    sys.exit(1)
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", test_script], capture_output=True, text=True
        )

        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"❌ 导入测试失败:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ 导入测试异常: {e}")
        return False


def test_server_startup():
    """测试服务器启动"""
    print("🔍 测试服务器启动...")

    try:
        # 启动服务器（测试模式）
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8001",
                "--reload",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # 等待服务器启动
        print("⏳ 等待服务器启动...")
        time.sleep(5)

        # 检查服务器是否响应
        try:
            response = requests.get("http://localhost:8001/", timeout=10)
            if response.status_code == 200:
                print("✅ 服务器启动成功")
                print(f"📊 响应状态: {response.status_code}")
                print(f"📄 响应内容: {response.json()}")

                # 测试健康检查端点
                health_response = requests.get(
                    "http://localhost:8001/health", timeout=10
                )
                if health_response.status_code == 200:
                    print("✅ 健康检查端点正常")
                    print(f"🏥 健康状态: {health_response.json()}")
                else:
                    print(f"⚠️ 健康检查端点异常: {health_response.status_code}")

                return True, process
            else:
                print(f"❌ 服务器响应异常: {response.status_code}")
                return False, process

        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到服务器: {e}")
            return False, process

    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        return False, None


def test_api_endpoints():
    """测试关键API端点"""
    print("🔍 测试API端点...")

    endpoints_to_test = [
        ("/", "GET", "根端点"),
        ("/health", "GET", "健康检查"),
        ("/api/v1/stats", "GET", "统计信息"),
    ]

    results = []

    for endpoint, method, description in endpoints_to_test:
        try:
            url = f"http://localhost:8001{endpoint}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                print(f"✅ {description} ({endpoint}): 正常")
                results.append(True)
            else:
                print(f"⚠️ {description} ({endpoint}): 状态码 {response.status_code}")
                results.append(False)

        except Exception as e:
            print(f"❌ {description} ({endpoint}): 错误 {e}")
            results.append(False)

    return all(results)


def cleanup_server(process):
    """清理服务器进程"""
    if process:
        print("🧹 清理服务器进程...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✅ 服务器进程已终止")
        except subprocess.TimeoutExpired:
            process.kill()
            print("🔪 强制终止服务器进程")


def main():
    """主测试流程"""
    print("🚀 开始本地部署测试")
    print("=" * 50)

    # 检查工作目录
    if not os.path.exists("main.py"):
        print("❌ 找不到main.py文件，请确保在正确的目录中运行")
        print(f"📁 当前目录: {os.getcwd()}")
        print(f"📄 目录内容: {os.listdir('.')}")
        return False

    # 步骤1: 语法检查
    if not test_python_syntax():
        print("❌ 语法检查失败，停止测试")
        return False

    # 步骤2: 导入检查
    if not test_imports():
        print("❌ 导入检查失败，停止测试")
        return False

    # 步骤3: 服务器启动测试
    server_ok, process = test_server_startup()
    if not server_ok:
        print("❌ 服务器启动失败")
        cleanup_server(process)
        return False

    try:
        # 步骤4: API端点测试
        if test_api_endpoints():
            print("✅ API端点测试通过")
            result = True
        else:
            print("⚠️ 部分API端点测试失败")
            result = False

    finally:
        # 清理
        cleanup_server(process)

    print("=" * 50)
    if result:
        print("🎉 本地部署测试完成 - 所有测试通过!")
        print("💡 修复成功，可以重新部署到云端")
    else:
        print("⚠️ 本地部署测试完成 - 存在一些问题")
        print("🔧 建议检查失败的测试项目")

    return result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
