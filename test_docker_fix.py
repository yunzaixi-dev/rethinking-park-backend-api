#!/usr/bin/env python3
"""
Docker部署修复验证脚本
"""

import subprocess
import time
import requests
import sys
import os

def test_docker_build():
    """测试Docker构建"""
    print("🔍 测试Docker构建...")
    
    try:
        result = subprocess.run([
            "docker", "build", "-t", "rethinking-park-test", "."
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Docker构建成功")
            return True
        else:
            print(f"❌ Docker构建失败:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Docker构建超时")
        return False
    except Exception as e:
        print(f"❌ Docker构建异常: {e}")
        return False

def test_docker_run():
    """测试Docker运行"""
    print("🔍 测试Docker运行...")
    
    try:
        # 启动容器
        process = subprocess.Popen([
            "docker", "run", "-d", "-p", "8002:8000", 
            "--name", "rethinking-park-test-container",
            "rethinking-park-test"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            container_id = stdout.decode().strip()
            print(f"✅ Docker容器启动成功: {container_id[:12]}")
            
            # 等待服务启动
            print("⏳ 等待服务启动...")
            time.sleep(10)
            
            # 测试服务响应
            try:
                response = requests.get("http://localhost:8002/", timeout=10)
                if response.status_code == 200:
                    print("✅ 服务响应正常")
                    print(f"📊 响应: {response.json()}")
                    return True, container_id
                else:
                    print(f"⚠️ 服务响应异常: {response.status_code}")
                    return False, container_id
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 无法连接到服务: {e}")
                return False, container_id
                
        else:
            print(f"❌ Docker容器启动失败:")
            print(stderr.decode())
            return False, None
            
    except Exception as e:
        print(f"❌ Docker运行异常: {e}")
        return False, None

def cleanup_docker(container_id=None):
    """清理Docker资源"""
    print("🧹 清理Docker资源...")
    
    if container_id:
        try:
            subprocess.run(["docker", "stop", container_id], 
                         capture_output=True, timeout=30)
            subprocess.run(["docker", "rm", container_id], 
                         capture_output=True, timeout=30)
            print("✅ 容器已清理")
        except Exception as e:
            print(f"⚠️ 容器清理失败: {e}")
    
    try:
        subprocess.run(["docker", "rmi", "rethinking-park-test"], 
                     capture_output=True, timeout=30)
        print("✅ 镜像已清理")
    except Exception as e:
        print(f"⚠️ 镜像清理失败: {e}")

def main():
    """主测试流程"""
    print("🚀 开始Docker修复验证")
    print("=" * 50)
    
    # 检查Docker是否可用
    try:
        subprocess.run(["docker", "--version"], 
                      capture_output=True, check=True)
        print("✅ Docker可用")
    except Exception:
        print("❌ Docker不可用，跳过Docker测试")
        return True
    
    container_id = None
    
    try:
        # 测试构建
        if not test_docker_build():
            print("❌ Docker构建测试失败")
            return False
        
        # 测试运行
        run_ok, container_id = test_docker_run()
        if not run_ok:
            print("❌ Docker运行测试失败")
            return False
        
        print("=" * 50)
        print("🎉 Docker修复验证完成 - 所有测试通过!")
        print("💡 可以安全地重新部署到云端")
        return True
        
    finally:
        cleanup_docker(container_id)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)