#!/usr/bin/env python3
"""
简单的部署验证脚本
快速检查API是否修复成功
"""

import requests
import json
import sys
from datetime import datetime

def test_api_basic():
    """测试基础API功能"""
    base_url = "https://api.rethinkingpark.com"
    
    print("🔍 测试API基础功能...")
    print(f"🌐 目标: {base_url}")
    print("-" * 40)
    
    tests = [
        ("根路径", "GET", "/"),
        ("健康检查", "GET", "/health"),
        ("统计信息", "GET", "/api/v1/stats"),
        ("详细健康检查", "GET", "/api/v1/health-detailed")
    ]
    
    results = []
    
    for name, method, endpoint in tests:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {name}: 正常 (200)")
                results.append(True)
                
                # 显示部分响应内容
                try:
                    data = response.json()
                    if 'status' in data:
                        print(f"   状态: {data['status']}")
                    if 'version' in data:
                        print(f"   版本: {data['version']}")
                except:
                    pass
                    
            elif response.status_code == 500:
                print(f"❌ {name}: 服务器错误 (500)")
                try:
                    error_data = response.json()
                    if 'details' in error_data and 'exception' in error_data['details']:
                        exception = error_data['details']['exception']
                        if "name 'time' is not defined" in exception:
                            print(f"   🚨 仍然存在time导入错误!")
                        else:
                            print(f"   错误: {exception}")
                except:
                    print(f"   原始错误: {response.text[:100]}")
                results.append(False)
            else:
                print(f"⚠️ {name}: 状态码 {response.status_code}")
                results.append(False)
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {name}: 连接错误 - {str(e)}")
            results.append(False)
        except Exception as e:
            print(f"❌ {name}: 异常 - {str(e)}")
            results.append(False)
    
    print("-" * 40)
    
    success_count = sum(results)
    total_count = len(results)
    success_rate = (success_count / total_count) * 100
    
    print(f"📊 测试结果: {success_count}/{total_count} 通过 ({success_rate:.1f}%)")
    
    if success_count == total_count:
        print("🎉 所有基础测试通过! API修复成功!")
        return True
    elif success_count > 0:
        print("⚠️ 部分测试通过，API部分功能正常")
        return False
    else:
        print("❌ 所有测试失败，API仍有问题")
        print("\n💡 建议:")
        print("1. 检查是否已推送修复代码到GitHub")
        print("2. 确认部署平台已拉取最新代码")
        print("3. 检查部署日志是否有错误")
        return False

def test_upload_simple():
    """简单测试图片上传功能"""
    print("\n🔍 测试图片上传功能...")
    
    try:
        # 创建一个简单的测试文件
        test_data = b"fake image data for testing"
        files = {'file': ('test.jpg', test_data, 'image/jpeg')}
        
        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/upload", 
            files=files, 
            timeout=15
        )
        
        if response.status_code == 200:
            print("✅ 图片上传: 正常")
            data = response.json()
            if 'image_hash' in data:
                print(f"   图片哈希: {data['image_hash']}")
            return True
        elif response.status_code == 500:
            print("❌ 图片上传: 服务器错误")
            try:
                error_data = response.json()
                if 'details' in error_data:
                    print(f"   错误详情: {error_data['details']}")
            except:
                pass
            return False
        else:
            print(f"⚠️ 图片上传: 状态码 {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 图片上传测试异常: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 API部署验证测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 基础功能测试
    basic_ok = test_api_basic()
    
    # 如果基础功能正常，测试上传功能
    upload_ok = False
    if basic_ok:
        upload_ok = test_upload_simple()
    
    print("=" * 50)
    
    if basic_ok and upload_ok:
        print("🎉 API修复验证成功! 所有核心功能正常")
        print("✅ 可以继续使用API进行开发")
        return True
    elif basic_ok:
        print("✅ 基础功能修复成功")
        print("⚠️ 上传功能可能需要进一步检查")
        return True
    else:
        print("❌ API仍有问题，需要进一步修复")
        print("\n🔧 下一步:")
        print("1. 确认修复代码已部署")
        print("2. 检查服务器日志")
        print("3. 验证环境配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)