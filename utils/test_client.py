#!/usr/bin/env python3
"""
简单的API测试客户端
用于测试图像上传和分析功能
"""

import requests
import json
import sys
import os
from typing import Optional

class RethinkingParkAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
    
    def health_check(self) -> dict:
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def upload_image(self, image_path: str) -> Optional[dict]:
        """上传图像"""
        try:
            if not os.path.exists(image_path):
                print(f"❌ 图像文件不存在: {image_path}")
                return None
            
            with open(image_path, 'rb') as f:
                files = {'file': (os.path.basename(image_path), f, 'image/jpeg')}
                response = requests.post(f"{self.api_base}/upload", files=files)
                response.raise_for_status()
                return response.json()
                
        except requests.RequestException as e:
            print(f"❌ 上传失败: {e}")
            return None
    
    def analyze_image(self, image_id: str, analysis_type: str = "comprehensive") -> Optional[dict]:
        """分析图像"""
        try:
            data = {
                "image_id": image_id,
                "analysis_type": analysis_type
            }
            response = requests.post(
                f"{self.api_base}/analyze",
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"❌ 分析失败: {e}")
            return None
    
    def get_image_info(self, image_id: str) -> Optional[dict]:
        """获取图像信息"""
        try:
            response = requests.get(f"{self.api_base}/image/{image_id}")
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"❌ 获取图像信息失败: {e}")
            return None
    
    def list_images(self, limit: int = 10) -> Optional[dict]:
        """列出图像"""
        try:
            response = requests.get(f"{self.api_base}/images?limit={limit}")
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"❌ 列出图像失败: {e}")
            return None
    
    def get_stats(self) -> Optional[dict]:
        """获取统计信息"""
        try:
            response = requests.get(f"{self.api_base}/stats")
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"❌ 获取统计信息失败: {e}")
            return None

def main():
    """主测试函数"""
    print("🚀 Rethinking Park API 测试客户端")
    print("=" * 50)
    
    # 创建客户端
    client = RethinkingParkAPIClient()
    
    # 健康检查
    print("\n1. 健康检查...")
    health = client.health_check()
    if "error" in health:
        print(f"❌ 服务不可用: {health['error']}")
        return
    print("✅ 服务正常运行")
    print(f"   状态: {health.get('status', 'unknown')}")
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("\n📖 使用方法:")
        print("   python utils/test_client.py <image_path>")
        print("   示例: python utils/test_client.py test_image.jpg")
        
        # 显示统计信息
        print("\n📊 当前统计信息:")
        stats = client.get_stats()
        if stats:
            print(f"   总图像数: {stats.get('total_images', 0)}")
            print(f"   已处理: {stats.get('processed_images', 0)}")
            print(f"   未处理: {stats.get('unprocessed_images', 0)}")
        
        # 列出现有图像
        print("\n📋 现有图像:")
        images = client.list_images()
        if images and len(images) > 0:
            for img in images:
                print(f"   - {img['filename']} (ID: {img['image_id'][:8]}...)")
        else:
            print("   无图像")
        
        return
    
    image_path = sys.argv[1]
    
    # 测试图像上传
    print(f"\n2. 上传图像: {image_path}")
    upload_result = client.upload_image(image_path)
    if not upload_result:
        return
    
    image_id = upload_result['image_id']
    print("✅ 上传成功")
    print(f"   图像ID: {image_id}")
    print(f"   文件大小: {upload_result['file_size']} 字节")
    print(f"   GCS URL: {upload_result['gcs_url'][:50]}...")
    
    # 测试图像分析
    print(f"\n3. 分析图像: {image_id[:8]}...")
    analysis_result = client.analyze_image(image_id, "comprehensive")
    if not analysis_result:
        return
    
    print("✅ 分析完成")
    print(f"   分析类型: {analysis_result['analysis_type']}")
    
    # 显示分析结果
    results = analysis_result['results']
    
    if 'labels' in results and results['labels']:
        print("\n🏷️  标签识别:")
        for label in results['labels'][:5]:  # 显示前5个
            print(f"   - {label['name']}: {label['confidence']:.2f}")
    
    if 'objects' in results and results['objects']:
        print("\n🎯 对象检测:")
        for obj in results['objects'][:3]:  # 显示前3个
            print(f"   - {obj['name']}: {obj['confidence']:.2f}")
    
    if 'text_detection' in results and results['text_detection']['full_text']:
        print("\n📝 文本识别:")
        text = results['text_detection']['full_text']
        print(f"   {text[:100]}{'...' if len(text) > 100 else ''}")
    
    # 获取图像信息
    print(f"\n4. 获取图像信息...")
    image_info = client.get_image_info(image_id)
    if image_info:
        print("✅ 图像信息获取成功")
        print(f"   处理状态: {'已处理' if image_info['processed'] else '未处理'}")
        print(f"   上传时间: {image_info['upload_time']}")
    
    print(f"\n🎉 测试完成! 图像ID: {image_id}")
    print(f"   您可以使用此ID进行进一步的分析或查询")

if __name__ == "__main__":
    main() 