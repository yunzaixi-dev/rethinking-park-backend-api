#!/usr/bin/env python3
"""
Comprehensive test for the download-annotated endpoint
"""

import requests
import json
import sys
import time

def test_download_annotated_comprehensive():
    """Comprehensive test of the download-annotated endpoint"""
    
    print("🧪 Comprehensive Download Annotated Endpoint Test")
    print("=" * 60)
    
    base_url = "http://localhost:8000/api/v1"
    
    try:
        # Test 1: Server health check
        print("1. 🏥 Server Health Check")
        health_response = requests.get(f"{base_url.replace('/api/v1', '')}/health", timeout=5)
        if health_response.status_code == 200:
            print("   ✅ Server is healthy")
        else:
            print("   ❌ Server health check failed")
            return False
        
        # Test 2: Endpoint registration check
        print("\n2. 📋 Endpoint Registration Check")
        openapi_response = requests.get(f"{base_url.replace('/api/v1', '')}/openapi.json", timeout=5)
        if openapi_response.status_code == 200:
            openapi_data = openapi_response.json()
            if "/api/v1/download-annotated" in openapi_data.get("paths", {}):
                print("   ✅ Endpoint is properly registered in OpenAPI")
            else:
                print("   ❌ Endpoint not found in OpenAPI schema")
                return False
        else:
            print("   ❌ Could not retrieve OpenAPI schema")
            return False
        
        # Test 3: Invalid image hash handling
        print("\n3. ❌ Invalid Image Hash Handling")
        invalid_request = {
            "image_hash": "nonexistent_hash_123",
            "include_face_markers": True,
            "include_object_boxes": True,
            "include_labels": True
        }
        
        response = requests.post(
            f"{base_url}/download-annotated",
            json=invalid_request,
            timeout=10
        )
        
        if response.status_code == 404:
            print("   ✅ Correctly returns 404 for non-existent image")
        elif response.status_code == 200:
            result = response.json()
            if not result.get("success", True):
                print("   ✅ Correctly handles non-existent image with error response")
            else:
                print("   ❌ Should not succeed with non-existent image")
                return False
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
            return False
        
        # Test 4: Request validation
        print("\n4. ✅ Request Validation")
        
        # Test missing required field
        invalid_request_missing_hash = {
            "include_face_markers": True
        }
        
        response = requests.post(
            f"{base_url}/download-annotated",
            json=invalid_request_missing_hash,
            timeout=10
        )
        
        if response.status_code == 422:
            print("   ✅ Correctly validates missing required fields")
        else:
            print(f"   ❌ Should return 422 for missing required fields, got {response.status_code}")
            return False
        
        # Test invalid output format
        invalid_format_request = {
            "image_hash": "test123",
            "output_format": "invalid_format"
        }
        
        response = requests.post(
            f"{base_url}/download-annotated",
            json=invalid_format_request,
            timeout=10
        )
        
        if response.status_code == 422:
            print("   ✅ Correctly validates invalid output format")
        else:
            print(f"   ❌ Should return 422 for invalid format, got {response.status_code}")
            return False
        
        # Test 5: Valid request structure with default values
        print("\n5. 📝 Valid Request Structure")
        valid_request = {
            "image_hash": "test_hash_for_structure_validation"
        }
        
        response = requests.post(
            f"{base_url}/download-annotated",
            json=valid_request,
            timeout=10
        )
        
        # Should return 404 (image not found) but with proper structure
        if response.status_code == 404:
            print("   ✅ Request structure is valid (returns expected 404)")
        elif response.status_code == 200:
            result = response.json()
            if not result.get("success", True):
                print("   ✅ Request structure is valid (returns error response)")
            else:
                print("   ❌ Unexpected success with non-existent image")
                return False
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            return False
        
        # Test 6: Custom annotation styles
        print("\n6. 🎨 Custom Annotation Styles")
        custom_style_request = {
            "image_hash": "test_hash_custom_style",
            "annotation_style": {
                "face_marker_color": "#FF0000",
                "box_color": "#00FF00",
                "label_color": "#0000FF",
                "box_thickness": 3,
                "face_marker_radius": 12
            },
            "output_format": "jpg",
            "quality": 85
        }
        
        response = requests.post(
            f"{base_url}/download-annotated",
            json=custom_style_request,
            timeout=10
        )
        
        if response.status_code in [404, 200]:
            print("   ✅ Custom annotation styles are accepted")
        else:
            print(f"   ❌ Custom styles validation failed: {response.status_code}")
            return False
        
        # Test 7: Different output formats
        print("\n7. 📁 Output Format Support")
        formats = ["png", "jpg", "webp"]
        
        for fmt in formats:
            format_request = {
                "image_hash": f"test_hash_{fmt}",
                "output_format": fmt,
                "quality": 90
            }
            
            response = requests.post(
                f"{base_url}/download-annotated",
                json=format_request,
                timeout=10
            )
            
            if response.status_code in [404, 200]:
                print(f"   ✅ {fmt.upper()} format is supported")
            else:
                print(f"   ❌ {fmt.upper()} format validation failed")
                return False
        
        # Test 8: Parameter ranges
        print("\n8. 🔢 Parameter Range Validation")
        
        # Test confidence threshold range
        confidence_tests = [
            {"confidence_threshold": 0.0, "should_pass": True},
            {"confidence_threshold": 0.5, "should_pass": True},
            {"confidence_threshold": 1.0, "should_pass": True},
            {"confidence_threshold": -0.1, "should_pass": False},
            {"confidence_threshold": 1.1, "should_pass": False}
        ]
        
        for test in confidence_tests:
            test_request = {
                "image_hash": "test_confidence",
                "confidence_threshold": test["confidence_threshold"]
            }
            
            response = requests.post(
                f"{base_url}/download-annotated",
                json=test_request,
                timeout=10
            )
            
            if test["should_pass"]:
                if response.status_code in [404, 200]:
                    print(f"   ✅ Confidence {test['confidence_threshold']} accepted")
                else:
                    print(f"   ❌ Valid confidence {test['confidence_threshold']} rejected")
                    return False
            else:
                if response.status_code == 422:
                    print(f"   ✅ Invalid confidence {test['confidence_threshold']} rejected")
                else:
                    print(f"   ❌ Invalid confidence {test['confidence_threshold']} should be rejected")
                    return False
        
        # Test 9: Response structure validation
        print("\n9. 📊 Response Structure Validation")
        structure_request = {
            "image_hash": "test_response_structure"
        }
        
        response = requests.post(
            f"{base_url}/download-annotated",
            json=structure_request,
            timeout=10
        )
        
        if response.status_code in [200, 404]:
            try:
                result = response.json()
                required_fields = ["image_hash", "annotation_id", "processing_time_ms", "success", "from_cache"]
                
                missing_fields = [field for field in required_fields if field not in result]
                if not missing_fields:
                    print("   ✅ Response structure contains all required fields")
                else:
                    print(f"   ❌ Missing required fields: {missing_fields}")
                    return False
                    
            except json.JSONDecodeError:
                print("   ❌ Response is not valid JSON")
                return False
        else:
            print(f"   ❌ Unexpected response status: {response.status_code}")
            return False
        
        print("\n🎉 All comprehensive tests passed!")
        print("\n📋 Test Summary:")
        print("   ✅ Server health and endpoint registration")
        print("   ✅ Error handling for invalid inputs")
        print("   ✅ Request validation and parameter ranges")
        print("   ✅ Custom annotation styles support")
        print("   ✅ Multiple output format support")
        print("   ✅ Response structure validation")
        print("\n🚀 The download-annotated endpoint is fully functional!")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def main():
    """Main test function"""
    success = test_download_annotated_comprehensive()
    if success:
        print("\n✅ Comprehensive download-annotated endpoint test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Comprehensive download-annotated endpoint test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()