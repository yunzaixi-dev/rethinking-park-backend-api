#!/usr/bin/env python3
"""
部署后完整功能测试
"""

import io
import json
import sys
from datetime import datetime

import requests
from PIL import Image


def create_and_upload_test_image():
    """创建并上传测试图片"""
    print("🎨 创建测试图片...")

    try:
        # 创建一个彩色测试图片
        img = Image.new("RGB", (300, 200))
        pixels = img.load()

        # 创建彩色渐变
        for x in range(300):
            for y in range(200):
                r = int(255 * x / 300)
                g = int(255 * y / 200)
                b = 100
                pixels[x, y] = (r, g, b)

        # 转换为字节
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=90)
        image_data = img_bytes.getvalue()

        print(f"✅ 创建了 {len(image_data)} 字节的测试图片")

        # 上传图片
        print("📤 上传测试图片...")
        files = {"file": ("test_deployment.jpg", image_data, "image/jpeg")}

        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/upload", files=files, timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            image_hash = data.get("image_hash")
            print(f"✅ 图片上传成功: {image_hash}")
            return image_hash
        else:
            print(f"❌ 图片上传失败: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ 创建/上传图片异常: {str(e)}")
        return None


def test_basic_analysis(image_hash):
    """测试基础分析功能"""
    print(f"\n🔬 测试基础分析功能...")

    try:
        payload = {"image_hash": image_hash, "analysis_type": "labels"}

        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/analyze", json=payload, timeout=60
        )

        print(f"📊 基础分析响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 基础分析修复成功!")
            print(f"   分析类型: {data.get('analysis_type', 'N/A')}")
            print(f"   成功状态: {data.get('success', False)}")
            print(f"   来自缓存: {data.get('from_cache', False)}")

            if "results" in data and data["results"]:
                results = data["results"]
                if "labels" in results and results["labels"]:
                    print(f"   检测到标签: {len(results['labels'])} 个")
                    for label in results["labels"][:3]:
                        desc = label.get("description", "N/A")
                        score = label.get("score", 0)
                        print(f"     - {desc}: {score:.2f}")
                else:
                    print("   未检测到标签")

            return True
        elif response.status_code == 500:
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", "")
                if (
                    "'CacheService' object has no attribute 'get_analysis_result'"
                    in error_detail
                ):
                    print("❌ 缓存服务修复尚未生效")
                    return False
                else:
                    print(f"⚠️ 其他服务器错误: {error_detail}")
                    return False
            except:
                print("❌ 服务器错误，无法解析响应")
                return False
        else:
            print(f"⚠️ 意外的响应状态码: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   错误详情: {error_data}")
            except:
                pass
            return False

    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        return False


def test_natural_elements_analysis(image_hash):
    """测试自然元素分析功能"""
    print(f"\n🌿 测试自然元素分析功能...")

    try:
        payload = {"image_hash": image_hash, "analysis_types": ["vegetation", "sky"]}

        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/analyze-nature",
            json=payload,
            timeout=60,
        )

        print(f"📊 自然元素分析响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 自然元素分析修复成功!")
            print(f"   成功状态: {data.get('success', False)}")
            print(f"   处理时间: {data.get('processing_time_ms', 'N/A')}ms")
            print(f"   来自缓存: {data.get('from_cache', False)}")

            if "results" in data and data["results"]:
                results = data["results"]
                if "natural_elements" in results:
                    elements = results["natural_elements"]
                    print(f"   自然元素检测:")
                    for element_type, info in elements.items():
                        if isinstance(info, dict) and "confidence" in info:
                            print(f"     - {element_type}: {info['confidence']:.2f}")

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
                print(f"   错误详情: {error_data}")
            except:
                pass
            return False

    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        return False


def test_enhanced_detection(image_hash):
    """测试增强检测功能"""
    print(f"\n🔍 测试增强检测功能...")

    try:
        payload = {
            "image_hash": image_hash,
            "detection_types": ["objects"],
            "confidence_threshold": 0.5,
        }

        response = requests.post(
            "https://api.rethinkingpark.com/api/v1/detect-objects-enhanced",
            json=payload,
            timeout=60,
        )

        print(f"📊 增强检测响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 增强检测功能正常!")
            print(f"   成功状态: {data.get('success', False)}")
            print(f"   处理时间: {data.get('processing_time_ms', 'N/A')}ms")

            if "detections" in data and data["detections"]:
                print(f"   检测到对象: {len(data['detections'])} 个")

            return True
        else:
            print(f"⚠️ 增强检测响应状态码: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        return False


def cleanup_test_image(image_hash):
    """清理测试图片"""
    if not image_hash:
        return

    print(f"\n🧹 清理测试图片...")

    try:
        response = requests.delete(
            f"https://api.rethinkingpark.com/api/v1/image/{image_hash}", timeout=30
        )

        if response.status_code == 200:
            print("✅ 测试图片已清理")
        else:
            print(f"⚠️ 测试图片清理失败: {response.status_code}")

    except Exception as e:
        print(f"❌ 清理异常: {str(e)}")


def main():
    """主函数"""
    print("🚀 部署后完整功能测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 创建并上传测试图片
    image_hash = create_and_upload_test_image()
    if not image_hash:
        print("❌ 无法创建测试图片，测试终止")
        return False

    try:
        # 测试各项功能
        basic_analysis_ok = test_basic_analysis(image_hash)
        natural_analysis_ok = test_natural_elements_analysis(image_hash)
        enhanced_detection_ok = test_enhanced_detection(image_hash)

        print("\n" + "=" * 60)
        print("📊 部署后测试结果:")
        print(f"   ✅ 基础分析功能: {'通过' if basic_analysis_ok else '❌ 失败'}")
        print(f"   ✅ 自然元素分析: {'通过' if natural_analysis_ok else '❌ 失败'}")
        print(f"   ✅ 增强检测功能: {'通过' if enhanced_detection_ok else '❌ 失败'}")

        success_count = sum(
            [basic_analysis_ok, natural_analysis_ok, enhanced_detection_ok]
        )
        total_count = 3
        success_rate = (success_count / total_count) * 100

        print(f"   📊 成功率: {success_rate:.1f}% ({success_count}/{total_count})")

        if success_count == total_count:
            print("\n🎉 所有修复已生效，API功能完全正常!")
            print("✅ 缓存服务修复成功")
            print("✅ 参数一致性修复成功")
            print("✅ 图片分析功能完全恢复")
            return True
        elif success_count > 0:
            print(f"\n⚠️ 部分功能正常 ({success_count}/{total_count})")
            print("🔧 部分修复可能需要更多时间生效")
            return False
        else:
            print("\n❌ 所有测试失败，修复可能未生效")
            return False

    finally:
        # 清理测试图片
        cleanup_test_image(image_hash)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
