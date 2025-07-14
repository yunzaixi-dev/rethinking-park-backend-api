#!/usr/bin/env python3
"""
Google Cloud Platform 配置测试脚本
用于验证GCP服务连接和配置是否正确
"""

import os
import sys
from dotenv import load_dotenv

def load_environment():
    """加载环境变量"""
    load_dotenv()
    
    required_vars = [
        'GOOGLE_CLOUD_PROJECT_ID',
        'GOOGLE_CLOUD_STORAGE_BUCKET', 
        'GOOGLE_APPLICATION_CREDENTIALS'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 缺少必要的环境变量:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n请检查.env文件配置")
        return False
    
    return True

def test_credentials_file():
    """测试密钥文件是否存在"""
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not os.path.exists(creds_path):
        print(f"❌ 密钥文件不存在: {creds_path}")
        print("   请确保service-account-key.json文件在正确位置")
        return False
    
    try:
        import json
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
            
        required_keys = ['type', 'project_id', 'private_key', 'client_email']
        missing_keys = [key for key in required_keys if key not in creds_data]
        
        if missing_keys:
            print(f"❌ 密钥文件格式不完整，缺少: {missing_keys}")
            return False
        
        print("✅ 密钥文件格式正确")
        print(f"   文件路径: {creds_path}")
        print(f"   服务账号: {creds_data.get('client_email', '未知')}")
        return True
        
    except json.JSONDecodeError:
        print("❌ 密钥文件不是有效的JSON格式")
        return False
    except Exception as e:
        print(f"❌ 读取密钥文件时出错: {e}")
        return False

def test_storage():
    """测试Cloud Storage连接"""
    try:
        from google.cloud import storage
        from google.cloud.exceptions import GoogleCloudError
        
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        bucket_name = os.getenv('GOOGLE_CLOUD_STORAGE_BUCKET')
        
        print(f"   项目ID: {project_id}")
        print(f"   存储桶: {bucket_name}")
        
        # 创建客户端
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        
        # 检查存储桶是否存在
        if bucket.exists():
            print("✅ Cloud Storage 连接成功")
            
            # 获取存储桶信息
            bucket.reload()
            print(f"   位置: {bucket.location}")
            print(f"   存储类别: {bucket.storage_class}")
            print(f"   创建时间: {bucket.time_created}")
            
            # 测试权限
            try:
                # 尝试列出对象（需要读权限）
                blobs = list(client.list_blobs(bucket_name, max_results=1))
                print("   ✓ 读权限正常")
                
                # 尝试创建测试对象（需要写权限）
                test_blob = bucket.blob("test-connection.txt")
                test_blob.upload_from_string("test", content_type="text/plain")
                print("   ✓ 写权限正常")
                
                # 删除测试对象
                test_blob.delete()
                print("   ✓ 删除权限正常")
                
            except Exception as e:
                print(f"   ⚠️ 权限测试失败: {e}")
            
            return True
        else:
            print("❌ 存储桶不存在")
            print("   请检查存储桶名称或创建存储桶")
            return False
            
    except ImportError:
        print("❌ google-cloud-storage 包未安装")
        print("   运行: pip install google-cloud-storage")
        return False
    except GoogleCloudError as e:
        print(f"❌ Google Cloud 错误: {e}")
        return False
    except Exception as e:
        print(f"❌ Cloud Storage 连接失败: {e}")
        return False

def test_vision():
    """测试Vision API连接"""
    try:
        from google.cloud import vision
        from google.cloud.exceptions import GoogleCloudError
        
        # 创建客户端
        client = vision.ImageAnnotatorClient()
        
        # 测试API连接（使用一个简单的标签检测）
        try:
            # 创建一个最小的测试图像（1x1像素白色PNG）
            import base64
            test_image_data = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
            )
            
            image = vision.Image(content=test_image_data)
            response = client.label_detection(image=image, max_results=1)
            
            print("✅ Vision API 连接成功")
            print("   ✓ 标签检测功能正常")
            
            # 测试其他功能
            try:
                response = client.object_localization(image=image, max_results=1)
                print("   ✓ 对象检测功能正常")
            except:
                print("   ⚠️ 对象检测可能需要更复杂的图像")
                
            return True
            
        except GoogleCloudError as e:
            if "quota" in str(e).lower():
                print("❌ Vision API 配额不足")
                print("   请检查API配额或启用计费")
            else:
                print(f"❌ Vision API 错误: {e}")
            return False
            
    except ImportError:
        print("❌ google-cloud-vision 包未安装")
        print("   运行: pip install google-cloud-vision")
        return False
    except Exception as e:
        print(f"❌ Vision API 连接失败: {e}")
        return False

def test_api_enabled():
    """检查API是否启用"""
    try:
        from google.cloud import service_usage_v1
        
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        client = service_usage_v1.ServiceUsageClient()
        
        project_path = f"projects/{project_id}"
        
        # 检查API服务状态
        services_to_check = [
            "storage-api.googleapis.com",
            "vision.googleapis.com"
        ]
        
        for service_name in services_to_check:
            try:
                service_path = f"{project_path}/services/{service_name}"
                service = client.get_service(name=service_path)
                
                if service.state == service_usage_v1.State.ENABLED:
                    print(f"   ✓ {service_name} 已启用")
                else:
                    print(f"   ❌ {service_name} 未启用")
                    
            except Exception as e:
                print(f"   ⚠️ 无法检查 {service_name}: {e}")
                
    except ImportError:
        print("   ⚠️ 无法检查API状态（需要google-cloud-service-usage）")
    except Exception as e:
        print(f"   ⚠️ API状态检查失败: {e}")

def main():
    """主测试函数"""
    print("🧪 Google Cloud Platform 配置测试")
    print("=" * 50)
    
    # 1. 检查环境变量
    print("\n1. 检查环境变量...")
    if not load_environment():
        sys.exit(1)
    print("✅ 环境变量配置正确")
    
    # 2. 检查密钥文件
    print("\n2. 检查密钥文件...")
    if not test_credentials_file():
        sys.exit(1)
    
    # 3. 检查API启用状态
    print("\n3. 检查API启用状态...")
    test_api_enabled()
    
    # 4. 测试Cloud Storage
    print("\n4. 测试Cloud Storage...")
    storage_ok = test_storage()
    
    # 5. 测试Vision API  
    print("\n5. 测试Vision API...")
    vision_ok = test_vision()
    
    # 6. 总结
    print("\n" + "=" * 50)
    print("📋 测试结果总结:")
    
    if storage_ok and vision_ok:
        print("🎉 所有服务配置正确！")
        print("\n✅ 你现在可以:")
        print("   - 启动API服务: python main.py")
        print("   - 测试图像上传: python utils/test_client.py <image_path>")
        print("   - 访问API文档: http://localhost:8000/docs")
        return 0
    else:
        print("⚠️  部分服务配置有问题，请检查上述错误信息")
        print("\n🔧 建议:")
        if not storage_ok:
            print("   - 检查存储桶配置和权限")
        if not vision_ok:
            print("   - 检查Vision API配置和配额")
        print("   - 参考文档: docs/google-cloud-setup.md")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 