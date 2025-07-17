#!/usr/bin/env python3
"""
Test script for batch processing functionality
Tests the BatchProcessingService and batch processing endpoints
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchProcessingTester:
    """Test class for batch processing functionality"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"

    def test_service_health(self) -> bool:
        """Test if the service is running"""
        try:
            response = requests.get(f"{self.base_url}/docs")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Service health check failed: {e}")
            return False

    def test_batch_processing_service_import(self) -> bool:
        """Test if batch processing service can be imported"""
        try:
            from services.batch_processing_service import batch_processing_service

            logger.info("✅ BatchProcessingService imported successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to import BatchProcessingService: {e}")
            return False

    def test_batch_processing_models(self) -> bool:
        """Test if batch processing models can be imported"""
        try:
            from models.image import (
                BatchJobStatus,
                BatchOperationRequest,
                BatchProcessingRequest,
                BatchProcessingResponse,
                BatchResultsResponse,
            )

            logger.info("✅ Batch processing models imported successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to import batch processing models: {e}")
            return False

    async def test_batch_service_functionality(self) -> bool:
        """Test batch processing service functionality"""
        try:
            from services.batch_processing_service import batch_processing_service

            # Test creating a batch job
            operations = [
                {
                    "type": "detect_objects",
                    "image_hash": "test_hash_1",
                    "parameters": {"confidence_threshold": 0.5},
                },
                {
                    "type": "analyze_labels",
                    "image_hash": "test_hash_2",
                    "parameters": {"target_categories": ["Plant", "Tree"]},
                },
            ]

            batch_id = await batch_processing_service.create_batch_job(
                operations=operations, callback_url=None, max_concurrent_operations=2
            )

            logger.info(f"✅ Created batch job: {batch_id}")

            # Test getting batch status
            status = await batch_processing_service.get_batch_status(batch_id)
            if status:
                logger.info(f"✅ Retrieved batch status: {status['status']}")
            else:
                logger.error("❌ Failed to retrieve batch status")
                return False

            # Test service statistics
            stats = batch_processing_service.get_service_statistics()
            logger.info(
                f"✅ Service statistics: {stats['total_jobs_created']} jobs created"
            )

            return True

        except Exception as e:
            logger.error(f"❌ Batch service functionality test failed: {e}")
            return False

    def create_sample_batch_request(self) -> Dict[str, Any]:
        """Create a sample batch processing request"""
        return {
            "operations": [
                {
                    "type": "detect_objects",
                    "image_hash": "sample_hash_1",
                    "parameters": {
                        "confidence_threshold": 0.5,
                        "include_faces": True,
                        "include_labels": True,
                        "max_results": 20,
                    },
                    "max_retries": 2,
                },
                {
                    "type": "analyze_labels",
                    "image_hash": "sample_hash_2",
                    "parameters": {
                        "target_categories": ["Plant", "Tree", "Sky", "Building"],
                        "include_confidence": True,
                        "confidence_threshold": 0.3,
                    },
                    "max_retries": 1,
                },
                {
                    "type": "analyze_nature",
                    "image_hash": "sample_hash_3",
                    "parameters": {
                        "analysis_depth": "comprehensive",
                        "include_health_assessment": True,
                    },
                    "max_retries": 2,
                },
            ],
            "callback_url": None,
            "max_concurrent_operations": 3,
        }

    def test_batch_endpoint_validation(self) -> bool:
        """Test batch processing endpoint validation"""
        try:
            # Test empty operations
            empty_request = {"operations": []}
            response = requests.post(
                f"{self.api_base}/batch-process", json=empty_request, timeout=10
            )

            if response.status_code == 400:
                logger.info("✅ Empty operations validation working")
            else:
                logger.warning(
                    f"⚠️ Unexpected response for empty operations: {response.status_code}"
                )

            # Test too many operations
            too_many_ops = {
                "operations": [
                    {
                        "type": "detect_objects",
                        "image_hash": f"hash_{i}",
                        "parameters": {},
                    }
                    for i in range(51)  # More than 50
                ]
            }

            response = requests.post(
                f"{self.api_base}/batch-process", json=too_many_ops, timeout=10
            )

            if response.status_code == 400:
                logger.info("✅ Too many operations validation working")
            else:
                logger.warning(
                    f"⚠️ Unexpected response for too many operations: {response.status_code}"
                )

            return True

        except Exception as e:
            logger.error(f"❌ Batch endpoint validation test failed: {e}")
            return False

    def test_batch_status_endpoint(self, batch_id: str = "nonexistent") -> bool:
        """Test batch status endpoint"""
        try:
            response = requests.get(
                f"{self.api_base}/batch-process/{batch_id}/status", timeout=10
            )

            if response.status_code == 404:
                logger.info(
                    "✅ Batch status endpoint returns 404 for nonexistent batch"
                )
                return True
            else:
                logger.warning(
                    f"⚠️ Unexpected response for nonexistent batch: {response.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Batch status endpoint test failed: {e}")
            return False

    def test_batch_statistics_endpoint(self) -> bool:
        """Test batch statistics endpoint"""
        try:
            response = requests.get(
                f"{self.api_base}/batch-process/statistics", timeout=10
            )

            if response.status_code == 200:
                stats = response.json()
                logger.info(f"✅ Batch statistics endpoint working: {stats}")
                return True
            else:
                logger.error(
                    f"❌ Batch statistics endpoint failed: {response.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Batch statistics endpoint test failed: {e}")
            return False

    def test_operation_types_validation(self) -> bool:
        """Test that all operation types are properly validated"""
        try:
            from services.batch_processing_service import BatchOperationType

            valid_types = [op.value for op in BatchOperationType]
            logger.info(f"✅ Valid operation types: {valid_types}")

            # Test invalid operation type
            invalid_request = {
                "operations": [
                    {
                        "type": "invalid_operation",
                        "image_hash": "test_hash",
                        "parameters": {},
                    }
                ]
            }

            response = requests.post(
                f"{self.api_base}/batch-process", json=invalid_request, timeout=10
            )

            if response.status_code == 400:
                logger.info("✅ Invalid operation type validation working")
                return True
            else:
                logger.warning(
                    f"⚠️ Invalid operation type not properly validated: {response.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Operation types validation test failed: {e}")
            return False

    async def run_comprehensive_test(self) -> Dict[str, bool]:
        """Run comprehensive test suite"""
        results = {}

        logger.info("🚀 Starting comprehensive batch processing tests...")

        # Test 1: Service health
        results["service_health"] = self.test_service_health()

        # Test 2: Import tests
        results["service_import"] = self.test_batch_processing_service_import()
        results["models_import"] = self.test_batch_processing_models()

        # Test 3: Service functionality (only if imports work)
        if results["service_import"]:
            results["service_functionality"] = (
                await self.test_batch_service_functionality()
            )
        else:
            results["service_functionality"] = False

        # Test 4: Endpoint tests (only if service is healthy)
        if results["service_health"]:
            results["endpoint_validation"] = self.test_batch_endpoint_validation()
            results["status_endpoint"] = self.test_batch_status_endpoint()
            results["statistics_endpoint"] = self.test_batch_statistics_endpoint()
            results["operation_types"] = self.test_operation_types_validation()
        else:
            logger.warning("⚠️ Skipping endpoint tests - service not healthy")
            results.update(
                {
                    "endpoint_validation": False,
                    "status_endpoint": False,
                    "statistics_endpoint": False,
                    "operation_types": False,
                }
            )

        return results

    def print_test_summary(self, results: Dict[str, bool]):
        """Print test results summary"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 BATCH PROCESSING TEST SUMMARY")
        logger.info("=" * 60)

        passed = sum(results.values())
        total = len(results)

        for test_name, passed_test in results.items():
            status = "✅ PASS" if passed_test else "❌ FAIL"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")

        logger.info("-" * 60)
        logger.info(f"Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        if passed == total:
            logger.info("🎉 All tests passed! Batch processing is working correctly.")
        else:
            logger.warning(
                f"⚠️ {total-passed} test(s) failed. Please check the implementation."
            )

        logger.info("=" * 60)


async def main():
    """Main test function"""
    tester = BatchProcessingTester()

    # Run comprehensive tests
    results = await tester.run_comprehensive_test()

    # Print summary
    tester.print_test_summary(results)

    # Return exit code based on results
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
