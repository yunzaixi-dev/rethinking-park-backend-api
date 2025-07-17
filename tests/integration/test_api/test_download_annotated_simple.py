#!/usr/bin/env python3
"""
Simple test for download-annotated endpoint
"""

import json
import sys

import requests


def test_download_annotated_api():
    """Test the download-annotated API endpoint"""

    print("🧪 Testing Download Annotated API Endpoint")
    print("=" * 50)

    # API base URL
    base_url = "http://localhost:8000/api/v1"

    try:
        # First, check if server is running
        health_response = requests.get(
            f"{base_url.replace('/api/v1', '')}/health", timeout=5
        )
        if health_response.status_code != 200:
            print("❌ Server is not running or not healthy")
            return False

        print("✅ Server is running and healthy")

        # Get list of available images
        images_response = requests.get(f"{base_url}/images?limit=1", timeout=10)
        if images_response.status_code != 200:
            print("❌ Could not get images list")
            return False

        images = images_response.json()
        if not images:
            print("❌ No images available for testing")
            return False

        test_image_hash = images[0]["image_hash"]
        print(f"📸 Using test image: {test_image_hash[:12]}...")

        # Test the download-annotated endpoint
        annotation_request = {
            "image_hash": test_image_hash,
            "include_face_markers": True,
            "include_object_boxes": True,
            "include_labels": True,
            "output_format": "png",
            "quality": 95,
            "confidence_threshold": 0.5,
            "max_objects": 50,
        }

        print("📤 Sending annotation request...")
        response = requests.post(
            f"{base_url}/download-annotated", json=annotation_request, timeout=30
        )

        print(f"📥 Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Annotation request successful!")
            print(f"   - Success: {result.get('success', False)}")
            print(f"   - Processing time: {result.get('processing_time_ms', 0)}ms")
            print(f"   - From cache: {result.get('from_cache', False)}")

            if result.get("result"):
                result_data = result["result"]
                print(
                    f"   - Annotated image URL: {result_data.get('annotated_image_url', 'N/A')}"
                )
                print(f"   - File size: {result_data.get('file_size', 0)} bytes")
                print(f"   - Format: {result_data.get('format', 'N/A')}")

                # Print annotation statistics
                stats = result_data.get("annotation_stats", {})
                print(f"   - Objects detected: {stats.get('total_objects', 0)}")
                print(f"   - Faces detected: {stats.get('total_faces', 0)}")

            return True
        else:
            print(f"❌ Request failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Error text: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(
            "❌ Could not connect to server. Make sure the server is running on localhost:8000"
        )
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def main():
    """Main test function"""
    success = test_download_annotated_api()
    if success:
        print("\n✅ Download annotated API test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Download annotated API test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
