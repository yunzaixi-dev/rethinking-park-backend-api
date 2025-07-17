#!/usr/bin/env python3
"""
测试增强功能：图像哈希、缓存、速率限制
"""

import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

import aiohttp

API_BASE_URL = "http://localhost:8000"


async def test_rate_limiting():
    """测试速率限制功能"""
    print("\n🔄 测试速率限制功能...")

    async with aiohttp.ClientSession() as session:
        # 快速发送多个请求测试速率限制
        start_time = time.time()
        success_count = 0
        rate_limited_count = 0

        for i in range(15):  # 超过每分钟10次的上传限制
            try:
                # 创建一个简单的测试图像
                test_data = f"test-image-{i}".encode()

                data = aiohttp.FormData()
                data.add_field(
                    "file",
                    test_data,
                    filename=f"test{i}.jpg",
                    content_type="image/jpeg",
                )

                async with session.post(
                    f"{API_BASE_URL}/api/v1/upload", data=data
                ) as response:
                    if response.status == 200:
                        success_count += 1
                        print(f"  ✅ 请求 {i+1}: 成功")
                    elif response.status == 429:
                        rate_limited_count += 1
                        print(f"  ⏱️ 请求 {i+1}: 速率限制")
                    else:
                        print(f"  ❌ 请求 {i+1}: 状态码 {response.status}")

            except Exception as e:
                print(f"  ❌ 请求 {i+1}: 错误 {e}")

        elapsed = time.time() - start_time
        print(f"\n速率限制测试结果:")
        print(f"  总请求数: 15")
        print(f"  成功请求: {success_count}")
        print(f"  被限制请求: {rate_limited_count}")
        print(f"  耗时: {elapsed:.2f}秒")

        if rate_limited_count > 0:
            print("  ✅ 速率限制功能正常工作")
        else:
            print("  ⚠️ 未触发速率限制，可能限制过宽松")


async def test_duplicate_detection():
    """测试重复图像检测"""
    print("\n🔄 测试重复图像检测...")

    async with aiohttp.ClientSession() as session:
        # 创建测试图像
        test_image_data = b"fake-image-data-for-testing-duplicate-detection"
        image_hash = hashlib.md5(test_image_data).hexdigest()

        # 第一次上传
        data1 = aiohttp.FormData()
        data1.add_field(
            "file", test_image_data, filename="original.jpg", content_type="image/jpeg"
        )

        async with session.post(
            f"{API_BASE_URL}/api/v1/upload", data=data1
        ) as response:
            if response.status == 200:
                result1 = await response.json()
                print(f"  ✅ 第一次上传成功: {result1.get('image_hash', '')[:8]}...")
                print(f"     是否重复: {result1.get('is_duplicate', False)}")
            else:
                print(f"  ❌ 第一次上传失败: {response.status}")
                return

        # 第二次上传相同图像
        data2 = aiohttp.FormData()
        data2.add_field(
            "file", test_image_data, filename="duplicate.jpg", content_type="image/jpeg"
        )

        async with session.post(
            f"{API_BASE_URL}/api/v1/upload", data=data2
        ) as response:
            if response.status == 200:
                result2 = await response.json()
                print(f"  ✅ 第二次上传响应: {result2.get('image_hash', '')[:8]}...")
                print(f"     是否重复: {result2.get('is_duplicate', False)}")
                print(f"     状态: {result2.get('status', '')}")

                if result2.get("is_duplicate"):
                    print("  ✅ 重复检测功能正常工作")
                else:
                    print("  ⚠️ 重复检测可能未生效")
            else:
                print(f"  ❌ 第二次上传失败: {response.status}")


async def test_hash_based_analysis():
    """测试基于哈希的图像分析"""
    print("\n🔄 测试基于哈希的图像分析...")

    async with aiohttp.ClientSession() as session:
        # 先上传一个图像
        test_image_data = b"fake-image-data-for-analysis-testing"

        data = aiohttp.FormData()
        data.add_field(
            "file",
            test_image_data,
            filename="analysis_test.jpg",
            content_type="image/jpeg",
        )

        async with session.post(f"{API_BASE_URL}/api/v1/upload", data=data) as response:
            if response.status != 200:
                print(f"  ❌ 上传失败: {response.status}")
                return

            upload_result = await response.json()
            image_hash = upload_result.get("image_hash")

            if not image_hash:
                print("  ❌ 未获取到图像哈希值")
                return

            print(f"  ✅ 图像上传成功，哈希: {image_hash[:8]}...")

        # 测试基于哈希的分析（第一次，应该调用Vision API）
        analysis_data = {
            "image_hash": image_hash,
            "analysis_type": "labels",
            "force_refresh": False,
        }

        start_time = time.time()
        async with session.post(
            f"{API_BASE_URL}/api/v1/analyze",
            json=analysis_data,
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status == 200:
                result1 = await response.json()
                elapsed1 = time.time() - start_time
                print(f"  ✅ 第一次分析完成 ({elapsed1:.2f}s)")
                print(f"     来自缓存: {result1.get('from_cache', False)}")
            else:
                print(f"  ❌ 第一次分析失败: {response.status}")
                error_text = await response.text()
                print(f"     错误: {error_text}")
                return

        # 测试第二次分析（应该从缓存获取）
        start_time = time.time()
        async with session.post(
            f"{API_BASE_URL}/api/v1/analyze",
            json=analysis_data,
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status == 200:
                result2 = await response.json()
                elapsed2 = time.time() - start_time
                print(f"  ✅ 第二次分析完成 ({elapsed2:.2f}s)")
                print(f"     来自缓存: {result2.get('from_cache', False)}")

                if result2.get("from_cache") and elapsed2 < elapsed1:
                    print("  ✅ 缓存功能正常工作")
                else:
                    print("  ⚠️ 缓存可能未生效")
            else:
                print(f"  ❌ 第二次分析失败: {response.status}")


async def test_system_stats():
    """测试系统统计功能"""
    print("\n🔄 测试系统统计...")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/api/v1/stats") as response:
            if response.status == 200:
                stats = await response.json()
                print("  ✅ 系统统计获取成功:")

                # 存储统计
                storage_stats = stats.get("storage", {})
                print(f"     总图像数: {storage_stats.get('total_images', 0)}")
                print(f"     唯一图像数: {storage_stats.get('unique_images', 0)}")
                print(f"     已处理图像: {storage_stats.get('processed_images', 0)}")
                print(f"     总大小: {storage_stats.get('total_size_mb', 0)}MB")

                # 缓存统计
                cache_stats = stats.get("cache", {})
                print(f"     缓存启用: {cache_stats.get('enabled', False)}")
                if cache_stats.get("enabled"):
                    print(f"     缓存连接: {cache_stats.get('connected', False)}")
                    print(f"     缓存键数: {cache_stats.get('total_keys', 0)}")

                # 系统配置
                system_stats = stats.get("system", {})
                print(
                    f"     重复检测: {system_stats.get('duplicate_detection', False)}"
                )
                print(f"     速率限制: {system_stats.get('rate_limit_enabled', False)}")
                print(f"     相似度阈值: {system_stats.get('similarity_threshold', 0)}")

            else:
                print(f"  ❌ 获取统计失败: {response.status}")


async def test_api_health():
    """测试API健康状态"""
    print("\n🔄 测试API健康状态...")

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/health") as response:
            if response.status == 200:
                health = await response.json()
                print("  ✅ 健康检查通过:")
                print(f"     状态: {health.get('status', 'unknown')}")

                storage_stats = health.get("storage_stats", {})
                print(
                    f"     存储系统: 正常 ({storage_stats.get('total_images', 0)} 图像)"
                )

                cache_stats = health.get("cache_stats", {})
                cache_status = "正常" if cache_stats.get("connected") else "离线"
                print(f"     缓存系统: {cache_status}")

            else:
                print(f"  ❌ 健康检查失败: {response.status}")


async def main():
    """主测试函数"""
    print("🚀 开始测试增强功能...")

    try:
        # 测试API基本连通性
        async with aiohttp.ClientSession() as session:
            async with session.get(API_BASE_URL) as response:
                if response.status != 200:
                    print(f"❌ API服务器连接失败: {response.status}")
                    print("请确保API服务器在 http://localhost:8000 运行")
                    return

        print("✅ API服务器连接正常")

        # 执行各项测试
        await test_api_health()
        await test_duplicate_detection()
        await test_hash_based_analysis()
        await test_rate_limiting()
        await test_system_stats()

        print("\n🎉 所有测试完成！")

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 检查依赖
    try:
        import aiohttp
    except ImportError:
        print("❌ 缺少依赖: pip install aiohttp")
        sys.exit(1)

    # 运行测试
    asyncio.run(main())
