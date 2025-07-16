#!/usr/bin/env python3
"""
Test script for the natural elements analysis endpoint
Tests the POST /api/v1/analyze-nature endpoint functionality
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
API_V1_STR = "/api/v1"

# Test image hash (should be an existing image in the system)
TEST_IMAGE_HASH = "test_image_hash_placeholder"

async def test_natural_elements_analysis():
    """Test the natural elements analysis endpoint"""
    print("🧪 Testing Natural Elements Analysis Endpoint")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Basic natural elements analysis
        print("\n1. Testing basic natural elements analysis...")
        
        basic_request = {
            "image_hash": TEST_IMAGE_HASH,
            "analysis_depth": "basic",
            "include_health_assessment": True,
            "include_seasonal_analysis": False,
            "include_color_analysis": False,
            "confidence_threshold": 0.3
        }
        
        try:
            async with session.post(
                f"{BASE_URL}{API_V1_STR}/analyze-nature",
                json=basic_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("   ✅ Basic analysis successful")
                    print(f"   Processing time: {result.get('processing_time_ms', 0)}ms")
                    print(f"   From cache: {result.get('from_cache', False)}")
                    
                    # Validate response structure
                    if 'results' in result:
                        results = result['results']
                        print(f"   Vegetation coverage: {results.get('vegetation_coverage', 0):.1f}%")
                        print(f"   Sky coverage: {results.get('sky_coverage', 0):.1f}%")
                        print(f"   Water coverage: {results.get('water_coverage', 0):.1f}%")
                        print(f"   Built environment: {results.get('built_environment_coverage', 0):.1f}%")
                        
                        if results.get('vegetation_health_score'):
                            print(f"   Vegetation health: {results['vegetation_health_score']:.1f}/100")
                        
                        print(f"   Analysis depth: {results.get('analysis_depth', 'unknown')}")
                        print(f"   Total labels analyzed: {results.get('total_labels_analyzed', 0)}")
                        print(f"   Overall assessment: {results.get('overall_assessment', 'unknown')}")
                        
                        if results.get('recommendations'):
                            print(f"   Recommendations: {len(results['recommendations'])} items")
                    
                elif response.status == 404:
                    print("   ⚠️  Image not found - this is expected if using placeholder hash")
                    error_detail = await response.json()
                    print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
                    
                elif response.status == 503:
                    print("   ⚠️  Vision service not available")
                    error_detail = await response.json()
                    print(f"   Error: {error_detail.get('detail', 'Service unavailable')}")
                    
                else:
                    print(f"   ❌ Unexpected status code: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text}")
                    
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        # Test 2: Comprehensive analysis with all features
        print("\n2. Testing comprehensive analysis with all features...")
        
        comprehensive_request = {
            "image_hash": TEST_IMAGE_HASH,
            "analysis_depth": "comprehensive",
            "include_health_assessment": True,
            "include_seasonal_analysis": True,
            "include_color_analysis": True,
            "confidence_threshold": 0.2
        }
        
        try:
            async with session.post(
                f"{BASE_URL}{API_V1_STR}/analyze-nature",
                json=comprehensive_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("   ✅ Comprehensive analysis successful")
                    print(f"   Processing time: {result.get('processing_time_ms', 0)}ms")
                    print(f"   From cache: {result.get('from_cache', False)}")
                    
                    if 'results' in result:
                        results = result['results']
                        
                        # Check comprehensive features
                        if results.get('vegetation_health_metrics'):
                            metrics = results['vegetation_health_metrics']
                            print(f"   Health metrics available:")
                            print(f"     Overall score: {metrics.get('overall_score', 0):.1f}")
                            print(f"     Color health: {metrics.get('color_health_score', 0):.1f}")
                            print(f"     Coverage health: {metrics.get('coverage_health_score', 0):.1f}")
                            print(f"     Health status: {metrics.get('health_status', 'unknown')}")
                        
                        if results.get('seasonal_analysis'):
                            seasonal = results['seasonal_analysis']
                            print(f"   Seasonal analysis:")
                            print(f"     Detected seasons: {seasonal.get('detected_seasons', [])}")
                            print(f"     Primary season: {seasonal.get('primary_season', 'unknown')}")
                        
                        if results.get('dominant_colors'):
                            colors = results['dominant_colors']
                            print(f"   Color analysis: {len(colors)} dominant colors")
                            print(f"   Color diversity: {results.get('color_diversity_score', 0):.1f}")
                        
                        if results.get('element_categories'):
                            categories = results['element_categories']
                            print(f"   Element categories: {len(categories)} detected")
                            for cat in categories[:3]:  # Show first 3
                                print(f"     {cat.get('category_name', 'Unknown')}: {cat.get('coverage_percentage', 0):.1f}%")
                    
                elif response.status in [404, 503]:
                    print("   ⚠️  Expected error (image not found or service unavailable)")
                else:
                    print(f"   ❌ Unexpected status: {response.status}")
                    
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        # Test 3: Test with different confidence thresholds
        print("\n3. Testing different confidence thresholds...")
        
        for threshold in [0.1, 0.5, 0.8]:
            threshold_request = {
                "image_hash": TEST_IMAGE_HASH,
                "analysis_depth": "basic",
                "include_health_assessment": False,
                "include_seasonal_analysis": False,
                "include_color_analysis": False,
                "confidence_threshold": threshold
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}{API_V1_STR}/analyze-nature",
                    json=threshold_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    print(f"   Threshold {threshold}: Status {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        if 'results' in result:
                            categories = result['results'].get('element_categories', [])
                            print(f"     Categories detected: {len(categories)}")
                    
            except Exception as e:
                print(f"   Threshold {threshold}: Failed - {e}")
        
        # Test 4: Test invalid requests
        print("\n4. Testing invalid requests...")
        
        invalid_requests = [
            {
                "description": "Missing image_hash",
                "request": {
                    "analysis_depth": "basic"
                }
            },
            {
                "description": "Invalid analysis_depth",
                "request": {
                    "image_hash": TEST_IMAGE_HASH,
                    "analysis_depth": "invalid_depth"
                }
            },
            {
                "description": "Invalid confidence_threshold",
                "request": {
                    "image_hash": TEST_IMAGE_HASH,
                    "confidence_threshold": 1.5  # Should be 0-1
                }
            }
        ]
        
        for test_case in invalid_requests:
            try:
                async with session.post(
                    f"{BASE_URL}{API_V1_STR}/analyze-nature",
                    json=test_case["request"],
                    headers={"Content-Type": "application/json"}
                ) as response:
                    print(f"   {test_case['description']}: Status {response.status}")
                    
                    if response.status == 422:
                        print("     ✅ Validation error as expected")
                    elif response.status == 400:
                        print("     ✅ Bad request as expected")
                    else:
                        print(f"     ⚠️  Unexpected status: {response.status}")
                        
            except Exception as e:
                print(f"   {test_case['description']}: Failed - {e}")

async def test_endpoint_availability():
    """Test if the endpoint is available and properly configured"""
    print("\n🔍 Testing endpoint availability...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test the root endpoint first
            async with session.get(f"{BASE_URL}/") as response:
                if response.status == 200:
                    print("   ✅ Server is running")
                    root_data = await response.json()
                    print(f"   Version: {root_data.get('version', 'unknown')}")
                    print(f"   Features: {root_data.get('features', {})}")
                else:
                    print(f"   ❌ Server not responding properly: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Cannot connect to server: {e}")
            print("   Make sure the server is running on http://localhost:8000")
            return False
    
    return True

async def get_available_images():
    """Get list of available images for testing"""
    print("\n📋 Getting available images...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}{API_V1_STR}/images?limit=5") as response:
                if response.status == 200:
                    images = await response.json()
                    if images:
                        print(f"   Found {len(images)} images:")
                        for img in images:
                            print(f"     - {img.get('image_hash', 'unknown')[:16]}... ({img.get('filename', 'unknown')})")
                        return images[0].get('image_hash') if images else None
                    else:
                        print("   No images found in system")
                        return None
                else:
                    print(f"   Failed to get images: {response.status}")
                    return None
                    
        except Exception as e:
            print(f"   Failed to get images: {e}")
            return None

async def main():
    """Main test function"""
    print("🚀 Natural Elements Analysis Endpoint Test")
    print("=" * 60)
    print(f"Testing endpoint: {BASE_URL}{API_V1_STR}/analyze-nature")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check if server is available
    if not await test_endpoint_availability():
        print("\n❌ Server is not available. Please start the server first.")
        sys.exit(1)
    
    # Try to get a real image hash for testing
    global TEST_IMAGE_HASH
    real_image_hash = await get_available_images()
    if real_image_hash:
        TEST_IMAGE_HASH = real_image_hash
        print(f"\n✅ Using real image hash: {TEST_IMAGE_HASH[:16]}...")
    else:
        print(f"\n⚠️  Using placeholder hash: {TEST_IMAGE_HASH}")
        print("   Some tests may fail due to missing image")
    
    # Run the main tests
    await test_natural_elements_analysis()
    
    print("\n" + "=" * 60)
    print("🏁 Natural Elements Analysis Endpoint Test Complete")
    print("\nNote: If you see 404 errors, make sure you have uploaded images to the system first.")
    print("You can upload images using the /api/v1/upload endpoint.")

if __name__ == "__main__":
    asyncio.run(main())