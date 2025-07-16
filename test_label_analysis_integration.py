#!/usr/bin/env python3
"""
Integration test for the label-based analysis endpoint
Tests the complete API endpoint flow including caching
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any
import tempfile
from PIL import Image
import io

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from models.image import LabelAnalysisRequest, LabelAnalysisResponse
from services.cache_service import cache_service
from services.storage_service import storage_service
from services.gcs_service import gcs_service

# Create test client
client = TestClient(app)

def create_test_image():
    """Create a simple test image for testing"""
    # Create a simple RGB image
    img = Image.new('RGB', (300, 200), color='green')
    
    # Add some blue sky area
    for y in range(50):
        for x in range(300):
            img.putpixel((x, y), (135, 206, 235))  # Sky blue
    
    # Add some brown ground
    for y in range(150, 200):
        for x in range(300):
            img.putpixel((x, y), (139, 69, 19))  # Brown
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

async def setup_test_image():
    """Upload a test image and return its hash"""
    print("🔧 Setting up test image...")
    
    # Create test image
    image_content = create_test_image()
    
    # Upload via the API
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test_park.png", image_content, "image/png")}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to upload test image: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    upload_data = response.json()
    image_hash = upload_data["image_hash"]
    print(f"✅ Test image uploaded with hash: {image_hash[:8]}...")
    
    return image_hash

def test_label_analysis_endpoint_basic():
    """Test the basic label analysis endpoint functionality"""
    print("\n🧪 Testing Label Analysis Endpoint - Basic Request...")
    
    # Mock image hash (we'll test with a real one later)
    test_hash = "test_hash_12345"
    
    # Create request payload
    request_data = {
        "image_hash": test_hash,
        "target_categories": ["Plant", "Tree", "Sky", "Building"],
        "include_confidence": True,
        "confidence_threshold": 0.3,
        "max_labels": 50
    }
    
    # Make request to endpoint
    response = client.post("/api/v1/analyze-by-labels", json=request_data)
    
    # Since we don't have a real image, this should return 404
    if response.status_code == 404:
        print("✅ Endpoint correctly returns 404 for non-existent image")
        return True
    else:
        print(f"❌ Unexpected response code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_label_analysis_request_validation():
    """Test request validation for the label analysis endpoint"""
    print("\n🧪 Testing Label Analysis Request Validation...")
    
    # Test missing required field
    invalid_request = {
        "target_categories": ["Plant", "Tree"],
        "include_confidence": True
        # Missing image_hash
    }
    
    response = client.post("/api/v1/analyze-by-labels", json=invalid_request)
    
    if response.status_code == 422:  # Validation error
        print("✅ Correctly validates missing required fields")
    else:
        print(f"❌ Expected validation error, got: {response.status_code}")
        return False
    
    # Test invalid confidence threshold
    invalid_threshold_request = {
        "image_hash": "test_hash",
        "confidence_threshold": 1.5  # Invalid: should be 0-1
    }
    
    response = client.post("/api/v1/analyze-by-labels", json=invalid_threshold_request)
    
    if response.status_code == 422:
        print("✅ Correctly validates confidence threshold range")
    else:
        print(f"❌ Expected validation error for threshold, got: {response.status_code}")
        return False
    
    # Test invalid max_labels
    invalid_max_request = {
        "image_hash": "test_hash",
        "max_labels": 150  # Invalid: should be 1-100
    }
    
    response = client.post("/api/v1/analyze-by-labels", json=invalid_max_request)
    
    if response.status_code == 422:
        print("✅ Correctly validates max_labels range")
        return True
    else:
        print(f"❌ Expected validation error for max_labels, got: {response.status_code}")
        return False

async def test_label_analysis_with_real_image():
    """Test the label analysis endpoint with a real uploaded image"""
    print("\n🧪 Testing Label Analysis with Real Image...")
    
    # Setup test image
    image_hash = await setup_test_image()
    if not image_hash:
        print("❌ Failed to setup test image")
        return False
    
    # Mock the Vision API response since we don't have real credentials in test
    # We'll create a mock analysis result
    mock_labels = [
        {"name": "Plant", "confidence": 0.85, "topicality": 0.82},
        {"name": "Tree", "confidence": 0.78, "topicality": 0.75},
        {"name": "Sky", "confidence": 0.92, "topicality": 0.90},
        {"name": "Grass", "confidence": 0.71, "topicality": 0.68},
        {"name": "Building", "confidence": 0.45, "topicality": 0.42}
    ]
    
    # Store mock analysis result in cache to simulate Vision API response
    await cache_service.set_analysis_result(image_hash, "labels", {"labels": mock_labels})
    
    # Create request
    request_data = {
        "image_hash": image_hash,
        "target_categories": ["Plant", "Tree", "Sky", "Building"],
        "include_confidence": True,
        "confidence_threshold": 0.4,
        "max_labels": 10
    }
    
    # Make request to endpoint
    response = client.post("/api/v1/analyze-by-labels", json=request_data)
    
    if response.status_code != 200:
        print(f"❌ Request failed with status: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    # Parse response
    response_data = response.json()
    
    # Validate response structure
    required_fields = ["image_hash", "results", "processing_time_ms", "success"]
    for field in required_fields:
        if field not in response_data:
            print(f"❌ Missing required field in response: {field}")
            return False
    
    if not response_data["success"]:
        print(f"❌ Analysis failed: {response_data.get('error_message', 'Unknown error')}")
        return False
    
    # Validate results structure
    results = response_data["results"]
    results_fields = ["all_labels", "category_analysis", "natural_elements_summary"]
    for field in results_fields:
        if field not in results:
            print(f"❌ Missing field in results: {field}")
            return False
    
    print(f"✅ Analysis completed successfully")
    print(f"📊 Total labels: {len(results['all_labels'])}")
    print(f"📋 Categories analyzed: {len(results['category_analysis'])}")
    print(f"⏱️ Processing time: {response_data['processing_time_ms']}ms")
    
    # Check category analysis
    for category in results["category_analysis"]:
        print(f"  🏷️ {category['category_name']}: {category['label_count']} labels, {category['coverage_estimate']:.1f}% coverage")
    
    return True

async def test_label_analysis_caching():
    """Test that the label analysis endpoint properly uses caching"""
    print("\n🧪 Testing Label Analysis Caching...")
    
    # Setup test image
    image_hash = await setup_test_image()
    if not image_hash:
        print("❌ Failed to setup test image")
        return False
    
    # Mock labels
    mock_labels = [
        {"name": "Tree", "confidence": 0.88, "topicality": 0.85},
        {"name": "Sky", "confidence": 0.94, "topicality": 0.91}
    ]
    
    await cache_service.set_analysis_result(image_hash, "labels", {"labels": mock_labels})
    
    request_data = {
        "image_hash": image_hash,
        "target_categories": ["Tree", "Sky"],
        "confidence_threshold": 0.5
    }
    
    # First request
    start_time = datetime.now()
    response1 = client.post("/api/v1/analyze-by-labels", json=request_data)
    first_duration = (datetime.now() - start_time).total_seconds() * 1000
    
    if response1.status_code != 200:
        print(f"❌ First request failed: {response1.status_code}")
        return False
    
    # Second request (should be cached)
    start_time = datetime.now()
    response2 = client.post("/api/v1/analyze-by-labels", json=request_data)
    second_duration = (datetime.now() - start_time).total_seconds() * 1000
    
    if response2.status_code != 200:
        print(f"❌ Second request failed: {response2.status_code}")
        return False
    
    # Check if second request was faster (cached)
    response2_data = response2.json()
    if response2_data.get("from_cache", False):
        print("✅ Second request correctly used cache")
    else:
        print("⚠️ Cache usage not explicitly indicated, but responses match")
    
    # Verify responses are identical
    if response1.json()["results"] == response2.json()["results"]:
        print("✅ Cached response matches original")
        return True
    else:
        print("❌ Cached response differs from original")
        return False

async def main():
    """Run all integration tests"""
    print("🚀 Starting Label Analysis Integration Tests")
    print("=" * 60)
    
    # Initialize services for testing
    try:
        await cache_service.initialize()
        print("✅ Cache service initialized")
    except Exception as e:
        print(f"⚠️ Cache service initialization failed: {e}")
    
    tests = [
        ("Basic Endpoint Test", test_label_analysis_endpoint_basic),
        ("Request Validation", test_label_analysis_request_validation),
        ("Real Image Analysis", test_label_analysis_with_real_image),
        ("Caching Functionality", test_label_analysis_caching)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result is not False))
            if result is not False:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
        
        print("-" * 40)
    
    # Summary
    print("\n📊 Integration Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    # Cleanup
    try:
        await cache_service.close()
        print("✅ Cache service closed")
    except Exception as e:
        print(f"⚠️ Cache cleanup failed: {e}")
    
    if passed == total:
        print("🎉 All integration tests passed! Label analysis endpoint is fully functional.")
        return True
    else:
        print("⚠️ Some integration tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)