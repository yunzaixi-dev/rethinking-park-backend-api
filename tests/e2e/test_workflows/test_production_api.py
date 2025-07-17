#!/usr/bin/env python3
"""
生产环境API全面测试脚本
测试 https://api.rethinkingpark.com/ 的所有端点
"""

import base64
import json
import os
import sys
import time
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

import requests
from PIL import Image


class APITester:
    def __init__(self, base_url: str = "https://api.rethinkingpark.com"):
        self.base_url = base_url.rstrip("/")
        self.api_v1 = f"{self.base_url}/api/v1"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "RethinkingPark-API-Tester/1.0"})
        self.test_results = []
        self.uploaded_images = []  # 存储上传的图片信息

    def log_test(self, endpoint: str, method: str, status: str, details: str = ""):
        """记录测试结果"""
        result = {
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {method} {endpoint} - {status}")
        if details:
            print(f"   {details}")

    def create_test_image(self) -> bytes:
        """创建一个测试图片"""
        img = Image.new("RGB", (100, 100), color="red")
        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG")
        return img_bytes.getvalue()

    def test_basic_endpoints(self):
        """测试基础端点"""
        print("🔍 测试基础端点...")

        # 测试根路径
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "/", "GET", "PASS", f"API版本: {data.get('version', 'N/A')}"
                )
            else:
                self.log_test("/", "GET", "FAIL", f"状态码: {response.status_code}")
        except Exception as e:
            self.log_test("/", "GET", "FAIL", f"异常: {str(e)}")

        # 测试健康检查
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "/health", "GET", "PASS", f"状态: {data.get('status', 'N/A')}"
                )
            else:
                self.log_test(
                    "/health", "GET", "FAIL", f"状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test("/health", "GET", "FAIL", f"异常: {str(e)}")

    def test_image_upload(self):
        """测试图片上传"""
        print("🔍 测试图片上传...")

        try:
            test_image = self.create_test_image()
            files = {"file": ("test.jpg", test_image, "image/jpeg")}

            response = self.session.post(f"{self.api_v1}/upload", files=files)

            if response.status_code == 200:
                data = response.json()
                image_hash = data.get("image_hash")
                if image_hash:
                    self.uploaded_images.append(image_hash)
                    self.log_test(
                        "/api/v1/upload", "POST", "PASS", f"图片哈希: {image_hash}"
                    )
                else:
                    self.log_test(
                        "/api/v1/upload", "POST", "FAIL", "响应中缺少image_hash"
                    )
            else:
                self.log_test(
                    "/api/v1/upload",
                    "POST",
                    "FAIL",
                    f"状态码: {response.status_code}, 响应: {response.text}",
                )
        except Exception as e:
            self.log_test("/api/v1/upload", "POST", "FAIL", f"异常: {str(e)}")

    def test_image_analysis(self):
        """测试图片分析"""
        print("🔍 测试图片分析...")

        if not self.uploaded_images:
            self.log_test("/api/v1/analyze", "POST", "SKIP", "没有可用的上传图片")
            return

        image_hash = self.uploaded_images[0]

        # 测试基础分析
        try:
            payload = {
                "image_hash": image_hash,
                "analysis_types": ["labels", "objects", "faces", "text"],
            }

            response = self.session.post(f"{self.api_v1}/analyze", json=payload)

            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "/api/v1/analyze",
                    "POST",
                    "PASS",
                    f"分析完成，标签数: {len(data.get('labels', []))}",
                )
            else:
                self.log_test(
                    "/api/v1/analyze", "POST", "FAIL", f"状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test("/api/v1/analyze", "POST", "FAIL", f"异常: {str(e)}")

        # 测试按ID分析
        try:
            payload = {"image_hash": image_hash}
            response = self.session.post(f"{self.api_v1}/analyze-by-id", json=payload)

            if response.status_code == 200:
                self.log_test("/api/v1/analyze-by-id", "POST", "PASS", "按ID分析成功")
            else:
                self.log_test(
                    "/api/v1/analyze-by-id",
                    "POST",
                    "FAIL",
                    f"状态码: {response.status_code}",
                )
        except Exception as e:
            self.log_test("/api/v1/analyze-by-id", "POST", "FAIL", f"异常: {str(e)}")

    def test_enhanced_detection(self):
        """测试增强检测功能"""
        print("🔍 测试增强检测功能...")

        if not self.uploaded_images:
            self.log_test(
                "/api/v1/detect-objects-enhanced", "POST", "SKIP", "没有可用的上传图片"
            )
            return

        image_hash = self.uploaded_images[0]

        try:
            payload = {
                "image_hash": image_hash,
                "detection_types": ["objects", "faces", "landmarks"],
                "confidence_threshold": 0.5,
            }

            response = self.session.post(
                f"{self.api_v1}/detect-objects-enhanced", json=payload
            )

            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "/api/v1/detect-objects-enhanced",
                    "POST",
                    "PASS",
                    f"检测到 {len(data.get('detections', []))} 个对象",
                )
            else:
                self.log_test(
                    "/api/v1/detect-objects-enhanced",
                    "POST",
                    "FAIL",
                    f"状态码: {response.status_code}",
                )
        except Exception as e:
            self.log_test(
                "/api/v1/detect-objects-enhanced", "POST", "FAIL", f"异常: {str(e)}"
            )

    def test_label_analysis(self):
        """测试标签分析"""
        print("🔍 测试标签分析...")

        if not self.uploaded_images:
            self.log_test(
                "/api/v1/analyze-by-labels", "POST", "SKIP", "没有可用的上传图片"
            )
            return

        image_hash = self.uploaded_images[0]

        try:
            payload = {
                "image_hash": image_hash,
                "target_labels": ["person", "car", "building"],
                "confidence_threshold": 0.5,
            }

            response = self.session.post(
                f"{self.api_v1}/analyze-by-labels", json=payload
            )

            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "/api/v1/analyze-by-labels",
                    "POST",
                    "PASS",
                    f"找到 {len(data.get('matching_labels', []))} 个匹配标签",
                )
            else:
                self.log_test(
                    "/api/v1/analyze-by-labels",
                    "POST",
                    "FAIL",
                    f"状态码: {response.status_code}",
                )
        except Exception as e:
            self.log_test(
                "/api/v1/analyze-by-labels", "POST", "FAIL", f"异常: {str(e)}"
            )

    def test_nature_analysis(self):
        """测试自然元素分析"""
        print("🔍 测试自然元素分析...")

        if not self.uploaded_images:
            self.log_test(
                "/api/v1/analyze-nature", "POST", "SKIP", "没有可用的上传图片"
            )
            return

        image_hash = self.uploaded_images[0]

        try:
            payload = {
                "image_hash": image_hash,
                "analysis_types": ["vegetation", "water", "sky", "terrain"],
            }

            response = self.session.post(f"{self.api_v1}/analyze-nature", json=payload)

            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "/api/v1/analyze-nature",
                    "POST",
                    "PASS",
                    f"自然元素分析完成，置信度: {data.get('overall_confidence', 0)}",
                )
            else:
                self.log_test(
                    "/api/v1/analyze-nature",
                    "POST",
                    "FAIL",
                    f"状态码: {response.status_code}",
                )
        except Exception as e:
            self.log_test("/api/v1/analyze-nature", "POST", "FAIL", f"异常: {str(e)}")

    def test_image_management(self):
        """测试图片管理功能"""
        print("🔍 测试图片管理功能...")

        # 测试图片列表
        try:
            response = self.session.get(f"{self.api_v1}/images?limit=10")

            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "/api/v1/images", "GET", "PASS", f"获取到 {len(data)} 张图片"
                )
            else:
                self.log_test(
                    "/api/v1/images", "GET", "FAIL", f"状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test("/api/v1/images", "GET", "FAIL", f"异常: {str(e)}")

        # 测试图片信息获取
        if self.uploaded_images:
            image_hash = self.uploaded_images[0]
            try:
                response = self.session.get(f"{self.api_v1}/image/{image_hash}")

                if response.status_code == 200:
                    self.log_test(
                        f"/api/v1/image/{image_hash}", "GET", "PASS", "图片信息获取成功"
                    )
                else:
                    self.log_test(
                        f"/api/v1/image/{image_hash}",
                        "GET",
                        "FAIL",
                        f"状态码: {response.status_code}",
                    )
            except Exception as e:
                self.log_test(
                    f"/api/v1/image/{image_hash}", "GET", "FAIL", f"异常: {str(e)}"
                )

        # 测试重复检查
        if self.uploaded_images:
            image_hash = self.uploaded_images[0]
            try:
                response = self.session.get(
                    f"{self.api_v1}/check-duplicate/{image_hash}"
                )

                if response.status_code == 200:
                    data = response.json()
                    self.log_test(
                        f"/api/v1/check-duplicate/{image_hash}",
                        "GET",
                        "PASS",
                        f"重复检查完成，是否重复: {data.get('is_duplicate', False)}",
                    )
                else:
                    self.log_test(
                        f"/api/v1/check-duplicate/{image_hash}",
                        "GET",
                        "FAIL",
                        f"状态码: {response.status_code}",
                    )
            except Exception as e:
                self.log_test(
                    f"/api/v1/check-duplicate/{image_hash}",
                    "GET",
                    "FAIL",
                    f"异常: {str(e)}",
                )

    def test_stats_and_metrics(self):
        """测试统计和指标端点"""
        print("🔍 测试统计和指标端点...")

        endpoints = [
            "/api/v1/stats",
            "/api/v1/health-detailed",
            "/api/v1/metrics",
            "/api/v1/vision-api-metrics",
            "/api/v1/cache-metrics",
            "/api/v1/batch-metrics",
            "/api/v1/performance-metrics",
        ]

        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")

                if response.status_code == 200:
                    self.log_test(endpoint, "GET", "PASS", "指标获取成功")
                else:
                    self.log_test(
                        endpoint, "GET", "FAIL", f"状态码: {response.status_code}"
                    )
            except Exception as e:
                self.log_test(endpoint, "GET", "FAIL", f"异常: {str(e)}")

    def test_batch_processing(self):
        """测试批处理功能"""
        print("🔍 测试批处理功能...")

        if not self.uploaded_images:
            self.log_test("/api/v1/batch-process", "POST", "SKIP", "没有可用的上传图片")
            return

        try:
            payload = {
                "image_hashes": self.uploaded_images[:1],  # 只用一张图片测试
                "processing_types": ["labels", "objects"],
                "batch_name": "API测试批处理",
            }

            response = self.session.post(f"{self.api_v1}/batch-process", json=payload)

            if response.status_code == 200:
                data = response.json()
                batch_id = data.get("batch_id")
                self.log_test(
                    "/api/v1/batch-process",
                    "POST",
                    "PASS",
                    f"批处理任务创建成功，ID: {batch_id}",
                )

                # 测试批处理状态查询
                if batch_id:
                    time.sleep(2)  # 等待一下
                    try:
                        status_response = self.session.get(
                            f"{self.api_v1}/batch-process/{batch_id}/status"
                        )
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            self.log_test(
                                f"/api/v1/batch-process/{batch_id}/status",
                                "GET",
                                "PASS",
                                f"状态: {status_data.get('status', 'N/A')}",
                            )
                        else:
                            self.log_test(
                                f"/api/v1/batch-process/{batch_id}/status",
                                "GET",
                                "FAIL",
                                f"状态码: {status_response.status_code}",
                            )
                    except Exception as e:
                        self.log_test(
                            f"/api/v1/batch-process/{batch_id}/status",
                            "GET",
                            "FAIL",
                            f"异常: {str(e)}",
                        )
            else:
                self.log_test(
                    "/api/v1/batch-process",
                    "POST",
                    "FAIL",
                    f"状态码: {response.status_code}",
                )
        except Exception as e:
            self.log_test("/api/v1/batch-process", "POST", "FAIL", f"异常: {str(e)}")

    def test_optimized_endpoints(self):
        """测试优化版本的端点"""
        print("🔍 测试优化版本端点...")

        if not self.uploaded_images:
            self.log_test("优化端点", "POST", "SKIP", "没有可用的上传图片")
            return

        image_hash = self.uploaded_images[0]

        # 测试优化版对象检测
        try:
            payload = {
                "image_hash": image_hash,
                "detection_types": ["objects"],
                "confidence_threshold": 0.5,
            }

            response = self.session.post(
                f"{self.api_v1}/detect-objects-optimized", json=payload
            )

            if response.status_code == 200:
                self.log_test(
                    "/api/v1/detect-objects-optimized",
                    "POST",
                    "PASS",
                    "优化版对象检测成功",
                )
            else:
                self.log_test(
                    "/api/v1/detect-objects-optimized",
                    "POST",
                    "FAIL",
                    f"状态码: {response.status_code}",
                )
        except Exception as e:
            self.log_test(
                "/api/v1/detect-objects-optimized", "POST", "FAIL", f"异常: {str(e)}"
            )

        # 测试优化版自然分析
        try:
            payload = {"image_hash": image_hash, "analysis_types": ["vegetation"]}

            response = self.session.post(
                f"{self.api_v1}/analyze-nature-optimized", json=payload
            )

            if response.status_code == 200:
                self.log_test(
                    "/api/v1/analyze-nature-optimized",
                    "POST",
                    "PASS",
                    "优化版自然分析成功",
                )
            else:
                self.log_test(
                    "/api/v1/analyze-nature-optimized",
                    "POST",
                    "FAIL",
                    f"状态码: {response.status_code}",
                )
        except Exception as e:
            self.log_test(
                "/api/v1/analyze-nature-optimized", "POST", "FAIL", f"异常: {str(e)}"
            )

    def cleanup_test_data(self):
        """清理测试数据"""
        print("🧹 清理测试数据...")

        for image_hash in self.uploaded_images:
            try:
                response = self.session.delete(f"{self.api_v1}/image/{image_hash}")
                if response.status_code == 200:
                    self.log_test(
                        f"/api/v1/image/{image_hash}",
                        "DELETE",
                        "PASS",
                        "测试图片删除成功",
                    )
                else:
                    self.log_test(
                        f"/api/v1/image/{image_hash}",
                        "DELETE",
                        "FAIL",
                        f"状态码: {response.status_code}",
                    )
            except Exception as e:
                self.log_test(
                    f"/api/v1/image/{image_hash}", "DELETE", "FAIL", f"异常: {str(e)}"
                )

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 API测试报告")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped_tests = len([r for r in self.test_results if r["status"] == "SKIP"])

        print(f"总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"⚠️ 跳过: {skipped_tests}")
        print(f"成功率: {(passed_tests/total_tests*100):.1f}%")

        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(
                        f"  - {result['method']} {result['endpoint']}: {result['details']}"
                    )

        # 保存详细报告
        report_data = {
            "test_summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "success_rate": passed_tests / total_tests * 100,
            },
            "test_results": self.test_results,
            "test_time": datetime.now().isoformat(),
        }

        with open("api_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: api_test_report.json")

        return failed_tests == 0

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始API全面测试")
        print(f"🌐 测试目标: {self.base_url}")
        print("=" * 60)

        try:
            # 基础测试
            self.test_basic_endpoints()

            # 图片上传测试
            self.test_image_upload()

            # 图片分析测试
            self.test_image_analysis()

            # 增强功能测试
            self.test_enhanced_detection()
            self.test_label_analysis()
            self.test_nature_analysis()

            # 图片管理测试
            self.test_image_management()

            # 统计和指标测试
            self.test_stats_and_metrics()

            # 批处理测试
            self.test_batch_processing()

            # 优化端点测试
            self.test_optimized_endpoints()

        finally:
            # 清理测试数据
            self.cleanup_test_data()

        # 生成报告
        return self.generate_report()


def main():
    """主函数"""
    base_url = "https://api.rethinkingpark.com"

    print(f"🔧 API测试工具")
    print(f"📡 目标API: {base_url}")

    tester = APITester(base_url)
    success = tester.run_all_tests()

    if success:
        print("\n🎉 所有测试通过！API运行正常")
        sys.exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查API状态")
        sys.exit(1)


if __name__ == "__main__":
    main()
