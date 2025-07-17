#!/usr/bin/env python3
"""
Test script for enhanced caching system for image processing results
Tests all the new caching functionality including TTL management, version management,
LRU eviction, cache statistics, and cache warming.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime
from typing import Any, Dict

from services.cache_service import cache_service


class EnhancedCacheSystemTester:
    """Test suite for enhanced caching system"""

    def __init__(self):
        self.test_results = []
        self.test_image_hashes = [
            "test_hash_001",
            "test_hash_002",
            "test_hash_003",
            "test_hash_004",
            "test_hash_005",
        ]

    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")

    async def test_cache_service_initialization(self):
        """Test cache service initialization and basic functionality"""
        try:
            # Test service availability
            is_enabled = cache_service.is_enabled()
            self.log_test_result(
                "Cache Service Initialization",
                is_enabled,
                f"Cache service enabled: {is_enabled}",
            )

            # Test basic stats
            stats = cache_service.get_stats()
            self.log_test_result(
                "Basic Cache Statistics",
                "enabled" in stats,
                f"Stats retrieved: {len(stats)} fields",
            )

        except Exception as e:
            self.log_test_result(
                "Cache Service Initialization", False, f"Error: {str(e)}"
            )

    async def test_detection_result_caching(self):
        """Test detection result caching with TTL management"""
        try:
            image_hash = self.test_image_hashes[0]

            # Test data
            detection_result = {
                "objects": [
                    {
                        "object_id": "obj_001",
                        "class_name": "tree",
                        "confidence": 0.85,
                        "bounding_box": {
                            "x": 0.1,
                            "y": 0.2,
                            "width": 0.3,
                            "height": 0.4,
                        },
                    }
                ],
                "faces": [],
                "labels": [{"name": "vegetation", "confidence": 0.9}],
                "detection_time": datetime.now().isoformat(),
            }

            # Test caching
            cache_success = await cache_service.set_detection_result(
                image_hash=image_hash,
                result=detection_result,
                confidence_threshold=0.5,
                include_faces=True,
                include_labels=True,
            )

            self.log_test_result(
                "Detection Result Caching - Set",
                cache_success,
                f"Cached detection result for {image_hash}",
            )

            # Test retrieval
            cached_result = await cache_service.get_detection_result(
                image_hash=image_hash,
                confidence_threshold=0.5,
                include_faces=True,
                include_labels=True,
            )

            retrieval_success = (
                cached_result is not None and len(cached_result.get("objects", [])) > 0
            )
            self.log_test_result(
                "Detection Result Caching - Get",
                retrieval_success,
                f"Retrieved cached result: {len(cached_result.get('objects', [])) if cached_result else 0} objects",
            )

        except Exception as e:
            self.log_test_result("Detection Result Caching", False, f"Error: {str(e)}")

    async def test_segmentation_mask_caching(self):
        """Test segmentation mask caching with extended TTL"""
        try:
            image_hash = self.test_image_hashes[1]
            object_id = "obj_001"

            # Test segmentation mask data
            mask_data = {
                "mask_url": f"gs://bucket/masks/{image_hash}_{object_id}.png",
                "algorithm": "basic",
                "confidence": 0.78,
                "processing_time": 2.5,
                "mask_size": {"width": 512, "height": 512},
            }

            # Test caching
            cache_success = await cache_service.set_segmentation_mask(
                image_hash=image_hash,
                object_id=object_id,
                mask_data=mask_data,
                algorithm="basic",
            )

            self.log_test_result(
                "Segmentation Mask Caching - Set",
                cache_success,
                f"Cached segmentation mask for {image_hash}/{object_id}",
            )

            # Test retrieval
            cached_mask = await cache_service.get_segmentation_mask(
                image_hash=image_hash, object_id=object_id, algorithm="basic"
            )

            retrieval_success = cached_mask is not None and "mask_url" in cached_mask
            self.log_test_result(
                "Segmentation Mask Caching - Get",
                retrieval_success,
                f"Retrieved cached mask: {cached_mask.get('algorithm') if cached_mask else 'None'}",
            )

        except Exception as e:
            self.log_test_result("Segmentation Mask Caching", False, f"Error: {str(e)}")

    async def test_extraction_result_caching(self):
        """Test extraction result caching with long TTL"""
        try:
            image_hash = self.test_image_hashes[2]
            object_id = "obj_002"

            extraction_params = {
                "output_format": "png",
                "add_padding": 10,
                "background_removal": True,
            }

            extraction_result = {
                "extracted_image_url": f"gs://bucket/extracted/{image_hash}_{object_id}.png",
                "original_size": {"width": 1024, "height": 768},
                "extracted_size": {"width": 256, "height": 192},
                "processing_method": "bounding_box",
                "extraction_time": 1.2,
            }

            # Test caching
            cache_success = await cache_service.set_extraction_result(
                image_hash=image_hash,
                object_id=object_id,
                result=extraction_result,
                extraction_params=extraction_params,
            )

            self.log_test_result(
                "Extraction Result Caching - Set",
                cache_success,
                f"Cached extraction result for {image_hash}/{object_id}",
            )

            # Test retrieval
            cached_result = await cache_service.get_extraction_result(
                image_hash=image_hash,
                object_id=object_id,
                extraction_params=extraction_params,
            )

            retrieval_success = (
                cached_result is not None and "extracted_image_url" in cached_result
            )
            self.log_test_result(
                "Extraction Result Caching - Get",
                retrieval_success,
                f"Retrieved cached extraction: {cached_result.get('processing_method') if cached_result else 'None'}",
            )

        except Exception as e:
            self.log_test_result("Extraction Result Caching", False, f"Error: {str(e)}")

    async def test_natural_elements_caching(self):
        """Test natural elements analysis result caching"""
        try:
            image_hash = self.test_image_hashes[3]

            natural_elements_result = {
                "vegetation_coverage": 65.5,
                "sky_coverage": 25.0,
                "water_coverage": 5.5,
                "built_environment_coverage": 4.0,
                "vegetation_health_score": 78.5,
                "dominant_colors": [
                    {"red": 45, "green": 120, "blue": 35, "hex_code": "#2d7823"}
                ],
                "seasonal_indicators": ["summer", "lush"],
                "analysis_time": datetime.now().isoformat(),
            }

            # Test caching
            cache_success = await cache_service.set_natural_elements_result(
                image_hash=image_hash,
                result=natural_elements_result,
                analysis_depth="comprehensive",
            )

            self.log_test_result(
                "Natural Elements Caching - Set",
                cache_success,
                f"Cached natural elements result for {image_hash}",
            )

            # Test retrieval
            cached_result = await cache_service.get_natural_elements_result(
                image_hash=image_hash, analysis_depth="comprehensive"
            )

            retrieval_success = (
                cached_result is not None
                and "vegetation_coverage" in cached_result
                and cached_result["vegetation_coverage"] == 65.5
            )

            self.log_test_result(
                "Natural Elements Caching - Get",
                retrieval_success,
                f"Retrieved natural elements: {cached_result.get('vegetation_coverage') if cached_result else 'None'}% vegetation",
            )

        except Exception as e:
            self.log_test_result("Natural Elements Caching", False, f"Error: {str(e)}")

    async def test_batch_processing_caching(self):
        """Test batch processing status caching with short TTL"""
        try:
            batch_id = "batch_001"

            batch_status = {
                "batch_id": batch_id,
                "status": "processing",
                "total_tasks": 5,
                "completed_tasks": 2,
                "failed_tasks": 0,
                "progress_percentage": 40.0,
                "estimated_completion": datetime.now().isoformat(),
            }

            # Test caching
            cache_success = await cache_service.set_batch_processing_status(
                batch_id=batch_id, status=batch_status
            )

            self.log_test_result(
                "Batch Processing Caching - Set",
                cache_success,
                f"Cached batch status for {batch_id}",
            )

            # Test retrieval
            cached_status = await cache_service.get_batch_processing_status(batch_id)

            retrieval_success = (
                cached_status is not None
                and cached_status.get("batch_id") == batch_id
                and cached_status.get("progress_percentage") == 40.0
            )

            self.log_test_result(
                "Batch Processing Caching - Get",
                retrieval_success,
                f"Retrieved batch status: {cached_status.get('progress_percentage') if cached_status else 'None'}% complete",
            )

        except Exception as e:
            self.log_test_result("Batch Processing Caching", False, f"Error: {str(e)}")

    async def test_version_management(self):
        """Test cache version management functionality"""
        try:
            image_hash = self.test_image_hashes[4]

            # Test versioned caching
            test_result = {
                "test_data": "version_test",
                "timestamp": datetime.now().isoformat(),
            }

            cache_success = await cache_service.set_cache_with_version_management(
                result_type="detection_results",
                image_hash=image_hash,
                result=test_result,
                version="v2",
                test_param="test_value",
            )

            self.log_test_result(
                "Version Management - Set",
                cache_success,
                f"Cached versioned result for {image_hash}",
            )

            # Test version info retrieval
            version_info = await cache_service.get_cache_version_info(
                "detection_results"
            )

            version_info_success = (
                version_info.get("enabled", False) and "version_counts" in version_info
            )

            self.log_test_result(
                "Version Management - Info",
                version_info_success,
                f"Version info retrieved: {len(version_info.get('version_counts', {}))} versions",
            )

        except Exception as e:
            self.log_test_result("Version Management", False, f"Error: {str(e)}")

    async def test_detailed_cache_statistics(self):
        """Test detailed cache statistics and monitoring"""
        try:
            # Get detailed statistics
            detailed_stats = await cache_service.get_detailed_cache_statistics()

            stats_success = (
                detailed_stats.get("enabled", False)
                and "redis_info" in detailed_stats
                and "application_stats" in detailed_stats
                and "type_statistics" in detailed_stats
                and "performance_metrics" in detailed_stats
            )

            self.log_test_result(
                "Detailed Cache Statistics",
                stats_success,
                f"Retrieved detailed stats with {len(detailed_stats.get('type_statistics', {}))} result types",
            )

            # Test performance metrics
            perf_metrics = detailed_stats.get("performance_metrics", {})
            metrics_success = (
                "cache_efficiency_score" in perf_metrics
                and "memory_efficiency" in perf_metrics
            )

            self.log_test_result(
                "Performance Metrics",
                metrics_success,
                f"Cache efficiency: {perf_metrics.get('cache_efficiency_score', 0):.1f}/100",
            )

        except Exception as e:
            self.log_test_result("Detailed Cache Statistics", False, f"Error: {str(e)}")

    async def test_cache_warming(self):
        """Test cache warming for common operations"""
        try:
            # Test cache warming
            warming_stats = await cache_service.warm_cache_for_common_operations(
                self.test_image_hashes[:3]
            )

            warming_success = (
                warming_stats.get("total_images", 0) == 3
                and "operations_attempted" in warming_stats
            )

            self.log_test_result(
                "Cache Warming",
                warming_success,
                f"Warmed cache for {warming_stats.get('total_images', 0)} images, "
                f"{len(warming_stats.get('operations_attempted', []))} operations attempted",
            )

        except Exception as e:
            self.log_test_result("Cache Warming", False, f"Error: {str(e)}")

    async def test_cache_cleanup(self):
        """Test cache cleanup and optimization"""
        try:
            # Test cache cleanup
            cleanup_stats = await cache_service.cleanup_expired_cache_entries()

            cleanup_success = (
                "total_keys_before" in cleanup_stats
                and "total_keys_after" in cleanup_stats
            )

            self.log_test_result(
                "Cache Cleanup",
                cleanup_success,
                f"Cleanup completed: {cleanup_stats.get('expired_keys_removed', 0)} expired, "
                f"{cleanup_stats.get('orphaned_keys_removed', 0)} orphaned keys removed",
            )

        except Exception as e:
            self.log_test_result("Cache Cleanup", False, f"Error: {str(e)}")

    async def test_lru_eviction(self):
        """Test LRU cache eviction policies"""
        try:
            # Test LRU eviction (with low memory limit to trigger eviction)
            eviction_stats = await cache_service.implement_lru_eviction(max_memory_mb=1)

            eviction_success = (
                "memory_before_mb" in eviction_stats
                and "eviction_needed" in eviction_stats
            )

            self.log_test_result(
                "LRU Eviction",
                eviction_success,
                f"LRU eviction: {eviction_stats.get('evicted_keys', 0)} keys evicted, "
                f"eviction needed: {eviction_stats.get('eviction_needed', False)}",
            )

        except Exception as e:
            self.log_test_result("LRU Eviction", False, f"Error: {str(e)}")

    async def run_all_tests(self):
        """Run all enhanced cache system tests"""
        print("🚀 Starting Enhanced Cache System Tests")
        print("=" * 60)

        # Run all tests
        await self.test_cache_service_initialization()
        await self.test_detection_result_caching()
        await self.test_segmentation_mask_caching()
        await self.test_extraction_result_caching()
        await self.test_natural_elements_caching()
        await self.test_batch_processing_caching()
        await self.test_version_management()
        await self.test_detailed_cache_statistics()
        await self.test_cache_warming()
        await self.test_cache_cleanup()
        await self.test_lru_eviction()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['details']}")

        print("\n🎉 Enhanced Cache System Testing Complete!")

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests) * 100,
            "test_results": self.test_results,
        }


async def main():
    """Main test execution function"""
    tester = EnhancedCacheSystemTester()
    results = await tester.run_all_tests()

    # Save detailed results to file
    with open("enhanced_cache_test_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Detailed test results saved to: enhanced_cache_test_results.json")

    return results


if __name__ == "__main__":
    asyncio.run(main())
