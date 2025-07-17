#!/usr/bin/env python3
"""
验证API修复是否生效的脚本
"""

import requests
import json
import sys
from datetime import datetime

def test_cache_service_fix():
    """测试缓存服务修复"""
    print("🔍 测试缓存服务修复...")
    
    try:
        # 测试基础分析
        payload = {
            "image_hash": "e91a2607b710ab74ec49ce3d4fa31682",
            "analysis_type": "labels"
        }
        
        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/analyze",
            json=payload,
            timeout=30
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 缓存服务修复成功!")
            data = response.json()
            print(f"   分析类型: {data.get('analysis_type', 'N/A')}")
            print(f"   成功状态: {data.get('success', False)}")
            return True
        elif response.status_code == 500:
            try:
                error_data = response.json()
                error_detail = error_data.get('detail', '')
                if "'CacheService' object has no attribute 'get_analysis_result'" in error_detail:
                    print("❌ 缓存服务修复尚未部署")
                    print("   错误: get_analysis_result 方法仍然缺失")
                    return False
                else:
                    print(f"⚠️ 其他服务器错误: {error_detail}")
                    return False
            except:
                print("❌ 服务器错误，无法解析响应")
                return False
        else:
            print(f"⚠️ 意外的响应状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        return False

def test_parameter_consistency():
    """测试参数一致性修复"""
    print("\n🔍 测试参数一致性修复...")
    
    try:
        # 测试自然元素分析的新参数
        payload = {
            "image_hash": "e91a2607b710ab74ec49ce3d4fa31682",
            "analysis_types": ["vegetation"]
        }
        
        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/analyze-nature",
            json=payload,
            timeout=30
        )
        
        print(f"📊 自然元素分析响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 参数一致性修复成功!")
            data = response.json()
            print(f"   处理时间: {data.get('processing_time_ms', 'N/A')}ms")
            print(f"   成功状态: {data.get('success', False)}")
            return True
        elif response.status_code == 422:
            try:
                error_data = response.json()
                print("❌ 参数验证失败")
                print(f"   错误详情: {error_data}")
                return False
            except:
                print("❌ 参数验证失败，无法解析错误")
                return False
        else:
            print(f"⚠️ 意外的响应状态码: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   响应内容: {error_data}")
            except:
                pass
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        return False

def test_image_upload_still_works():
    """确认图片上传功能仍然正常"""
    print("\n🔍 确认图片上传功能...")
    
    try:
        # 创建一个小的测试图片
        from PIL import Image
        import io
        
        img = Image.new('RGB', (50, 50), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        
        files = {'file': ('test_blue.jpg', img_bytes.getvalue(), 'image/jpeg')}
        
        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/upload",
            files=files,
            timeout=30
        )
        
        print(f"📊 上传响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 图片上传功能正常!")
            print(f"   图片哈希: {data.get('image_hash', 'N/A')}")
            
            # 清理测试图片
            image_hash = data.get('image_hash')
            if image_hash:
                delete_response = requests.delete(
                    f"https://api.rethinkingpark.com/api/v1/image/{image_hash}",
                    timeout=30
                )
                if delete_response.status_code == 200:
                    print("   测试图片已清理")
            
            return True
        else:
            print(f"❌ 图片上传失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        return False

def main():
    """主函数"""
    print("🔧 API修复验证工具")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # 测试各项修复
    cache_fix_ok = test_cache_service_fix()
    param_fix_ok = test_parameter_consistency()
    upload_still_ok = test_image_upload_still_works()
    
    print("\n" + "="*50)
    print("📊 修复验证结果:")
    print(f"   ✅ 缓存服务修复: {'通过' if cache_fix_ok else '❌ 未部署'}")
    print(f"   ✅ 参数一致性修复: {'通过' if param_fix_ok else '❌ 未部署'}")
    print(f"   ✅ 图片上传功能: {'正常' if upload_still_ok else '❌ 异常'}")
    
    if cache_fix_ok and param_fix_ok and upload_still_ok:
        print("\n🎉 所有修复已生效，API功能完全正常!")
        return True
    elif upload_still_ok:
        print("\n⚠️ 核心功能正常，但部分修复尚未部署")
        print("💡 建议: 重新部署最新代码到生产环境")
        return False
    else:
        print("\n❌ 发现严重问题，需要立即检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)