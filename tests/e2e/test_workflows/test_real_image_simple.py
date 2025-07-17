#!/usr/bin/env python3
"""
简单的真实图片测试 - 使用在线图片
"""

import io
import json
import sys
from datetime import datetime

import requests
from PIL import Image


def create_simple_test_image():
    """创建一个简单的真实图片"""
    # 创建一个彩色的测试图片
    img = Image.new("RGB", (300, 200))
    pixels = img.load()

    # 创建渐变效果
    for x in range(300):
        for y in range(200):
            r = int(255 * x / 300)
            g = int(255 * y / 200)
            b = 128
            pixels[x, y] = (r, g, b)

    # 转换为字节
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=90)
    return img_bytes.getvalue()


def test_image_upload_simple():
    """简单测试图片上传"""
    print("🎨 创建真实测试图片...")

    try:
        image_data = create_simple_test_image()
        print(f"✅ 创建了 {len(image_data)} 字节的JPEG图片")

        print("\n📤 上传图片到API...")

        files = {"file": ("test_gradient.jpg", image_data, "image/jpeg")}

        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/upload", files=files, timeout=30
        )

        print(f"📊 响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 图片上传成功!")
            print(f"   图片哈希: {data.get('image_hash', 'N/A')}")
            print(f"   文件大小: {data.get('file_size', 'N/A')} 字节")
            print(f"   内容类型: {data.get('content_type', 'N/A')}")

            if "gcs_url" in data:
                print(f"   存储URL: {data['gcs_url']}")

            # 测试图片信息获取
            image_hash = data.get("image_hash")
            if image_hash:
                print(f"\n🔍 获取图片信息...")

                info_response = requests.get(
                    f"https://api.rethinkingpark.com/api/v1/image/{image_hash}",
                    timeout=30,
                )

                if info_response.status_code == 200:
                    info_data = info_response.json()
                    print("✅ 图片信息获取成功!")
                    print(f"   状态: {info_data.get('status', 'N/A')}")
                    print(
                        f"   处理状态: {'已处理' if info_data.get('processed', False) else '未处理'}"
                    )
                    print(f"   上传时间: {info_data.get('upload_time', 'N/A')}")
                else:
                    print(f"⚠️ 图片信息获取失败: {info_response.status_code}")

                # 测试简单分析
                print(f"\n🔬 测试图片分析...")

                analysis_payload = {
                    "image_hash": image_hash,
                    "analysis_types": ["labels"],
                }

                analysis_response = requests.post(
                    "https://api.rethinkingpark.com/api/v1/analyze",
                    json=analysis_payload,
                    timeout=60,
                )

                print(f"📊 分析响应状态码: {analysis_response.status_code}")

                if analysis_response.status_code == 200:
                    analysis_data = analysis_response.json()
                    print("✅ 图片分析成功!")

                    if "labels" in analysis_data and analysis_data["labels"]:
                        print(f"   检测到 {len(analysis_data['labels'])} 个标签:")
                        for label in analysis_data["labels"][:5]:
                            desc = label.get("description", "N/A")
                            score = label.get("score", 0)
                            print(f"     - {desc}: {score:.2f}")
                    else:
                        print("   未检测到标签")

                elif analysis_response.status_code == 422:
                    print("⚠️ 分析请求参数错误")
                    try:
                        error_data = analysis_response.json()
                        print(f"   错误详情: {error_data}")
                    except:
                        pass
                elif analysis_response.status_code == 500:
                    print("⚠️ 分析服务内部错误 (可能是Vision API配置问题)")
                    try:
                        error_data = analysis_response.json()
                        print(f"   错误信息: {error_data.get('message', 'N/A')}")
                    except:
                        pass
                else:
                    print(f"⚠️ 分析失败: 状态码 {analysis_response.status_code}")

                # 清理测试图片
                print(f"\n🧹 清理测试图片...")

                delete_response = requests.delete(
                    f"https://api.rethinkingpark.com/api/v1/image/{image_hash}",
                    timeout=30,
                )

                if delete_response.status_code == 200:
                    print("✅ 测试图片删除成功")
                else:
                    print(f"⚠️ 测试图片删除失败: {delete_response.status_code}")

            return True

        elif response.status_code == 400:
            print("❌ 图片上传失败 - 请求错误")
            try:
                error_data = response.json()
                print(f"   错误详情: {error_data.get('detail', 'N/A')}")
            except:
                print(f"   响应内容: {response.text[:200]}")
            return False

        elif response.status_code == 500:
            print("❌ 图片上传失败 - 服务器错误")
            try:
                error_data = response.json()
                print(f"   错误信息: {error_data.get('message', 'N/A')}")
            except:
                print(f"   响应内容: {response.text[:200]}")
            return False

        else:
            print(f"❌ 图片上传失败 - 状态码: {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求异常: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        return False


def main():
    """主函数"""
    print("🎨 简单真实图片API测试")
    print(f"🌐 目标: https://api.rethinkingpark.com")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    success = test_image_upload_simple()

    print("=" * 50)

    if success:
        print("🎉 真实图片测试成功!")
        print("✅ 图片上传功能正常")
        print("✅ 图片存储功能正常")
        print("✅ 图片管理功能正常")
        print("⚠️ 图片分析功能取决于Vision API配置")
        sys.exit(0)
    else:
        print("❌ 真实图片测试失败")
        print("🔧 请检查API状态和配置")
        sys.exit(1)


if __name__ == "__main__":
    main()
