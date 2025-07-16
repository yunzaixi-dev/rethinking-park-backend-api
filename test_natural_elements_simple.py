#!/usr/bin/env python3
"""
Simple test script for the natural elements analysis endpoint
Tests the POST /api/v1/analyze-nature endpoint functionality using requests
"""

import requests
import json
import sys
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
API_V1_STR = "/api/v1"

def test_server_availability():
    """Test if the server is running"""
    print("🔍 Testing server availability...")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is running")
            data = response.json()
            print(f"   Version: {data.get('version', 'unknown')}")
            return True
        else:
            print(f"   ❌ Server responded with status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to server")
        print("   Make sure the server is running: python main.py")
        return False
    except Exception as e:
        print(f"   ❌ Error connecting to server: {e}")
        return False

def get_test_image_hash():
    """Get an available image hash for testing"""
    print("\n📋 Getting available images...")
    
    try:
        response = requests.get(f"{BASE_URL}{API_V1_STR}/images?limit=1", timeout=10)
        if response.status_code == 200:
            images = response.json()
            if images:
                image_hash = images[0].get('image_hash')
                print(f"   ✅ Found test image: {image_hash[:16]}...")
                return image_hash
            else:
                print("   ⚠️  No images found in system")
                return None
        else:
            print(f"   ❌ Failed to get images: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Error getting images: {e}")
        return None

def test_natural_elements_endpoint():
    """Test the natural elements analysis endpoint"""
    print("\n🧪 Testing Natural Elements Analysis Endpoint")
    print("=" * 60)
    
    # Get a test image hash
    test_image_hash = get_test_image_hash()
    if not test_image_hash:
        print("   ⚠️  Using placeholder hash for testing")
        test_image_hash = "placeholder_hash"
    
    # Test 1: Basic natural elements analysis
    print("\n1. Testing basic natural elements analysis...")
    
    basic_request = {
        "image_hash": test_image_hash,
        "analysis_depth": "basic",
        "include_health_assessment": True,
        "include_seasonal_analysis": False,
        "include_color_analysis": False,
        "confidence_threshold": 0.3
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}{API_V1_STR}/analyze-nature",
            json=basic_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ Basic analysis successful")
            print(f"   Processing time: {result.get('processing_time_ms', 0)}ms")
            print(f"   From cache: {result.get('from_cache', False)}")
            print(f"   Success: {result.get('success', False)}")
            print(f"   Enabled: {result.get('enabled', False)}")
            
            # Validate response structure
            if result.get('results'):
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
                    for i, rec in enumerate(results['recommendations'][:3]):  # Show first 3
                        print(f"     {i+1}. {rec}")
            else:
                print("   ⚠️  No results in response")
                
        elif response.status_code == 404:
            print("   ⚠️  Image not found - expected if using placeholder")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
            except:
                print(f"   Error text: {response.text}")
                
        elif response.status_code == 503:
            print("   ⚠️  Vision service not available")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail.get('detail', 'Service unavailable')}")
            except:
                print(f"   Error text: {response.text}")
                
        elif response.status_code == 422:
            print("   ❌ Validation error")
            try:
                error_detail = response.json()
                print(f"   Validation errors: {error_detail}")
            except:
                print(f"   Error text: {response.text}")
                
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out")
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 2: Comprehensive analysis
    print("\n2. Testing comprehensive analysis...")
    
    comprehensive_request = {
        "image_hash": test_image_hash,
        "analysis_depth": "comprehensive",
        "include_health_assessment": True,
        "include_seasonal_analysis": True,
        "include_color_analysis": True,
        "confidence_threshold": 0.2
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}{API_V1_STR}/analyze-nature",
            json=comprehensive_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ Comprehensive analysis successful")
            print(f"   Processing time: {result.get('processing_time_ms', 0)}ms")
            
            if result.get('results'):
                results = result['results']
                
                # Check comprehensive features
                if results.get('vegetation_health_metrics'):
                    metrics = results['vegetation_health_metrics']
                    print(f"   Health metrics available:")
                    print(f"     Overall score: {metrics.get('overall_score', 0):.1f}")
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
        
        elif response.status_code in [404, 503]:
            print("   ⚠️  Expected error (image not found or service unavailable)")
        else:
            print(f"   Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")
    
    # Test 3: Invalid request
    print("\n3. Testing invalid request...")
    
    invalid_request = {
        "image_hash": test_image_hash,
        "analysis_depth": "invalid_depth"  # Should cause validation error
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}{API_V1_STR}/analyze-nature",
            json=invalid_request,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 422:
            print("   ✅ Validation error as expected")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

def main():
    """Main test function"""
    print("🚀 Natural Elements Analysis Endpoint Test")
    print("=" * 60)
    print(f"Testing endpoint: {BASE_URL}{API_V1_STR}/analyze-nature")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check if server is available
    if not test_server_availability():
        print("\n❌ Server is not available. Please start the server first:")
        print("   python main.py")
        sys.exit(1)
    
    # Run the main tests
    test_natural_elements_endpoint()
    
    print("\n" + "=" * 60)
    print("🏁 Natural Elements Analysis Endpoint Test Complete")
    print("\nNote: If you see 404 errors, make sure you have uploaded images to the system first.")
    print("You can upload images using the /api/v1/upload endpoint.")

if __name__ == "__main__":
    main()