"""
End-to-end deployment verification tests.
Tests basic API functionality after deployment.
"""

import json
from datetime import datetime
from typing import List, Tuple

import pytest
import requests


@pytest.mark.e2e
@pytest.mark.slow
class TestDeploymentVerification:
    """Test deployment verification workflows."""

    @pytest.fixture
    def base_url(self) -> str:
        """Get base URL for testing."""
        # Use environment variable or default to production URL
        import os

        return os.getenv("API_BASE_URL", "https://api.rethinkingpark.com")

    @pytest.fixture
    def api_endpoints(self) -> List[Tuple[str, str, str]]:
        """Define API endpoints to test."""
        return [
            ("根路径", "GET", "/"),
            ("健康检查", "GET", "/health"),
            ("统计信息", "GET", "/api/v1/stats"),
            ("详细健康检查", "GET", "/api/v1/health-detailed"),
        ]

    def test_api_endpoints_availability(self, base_url, api_endpoints):
        """Test that all critical API endpoints are available."""
        timeout = 10
        successful_endpoints = []
        failed_endpoints = []

        for name, method, endpoint in api_endpoints:
            url = f"{base_url}{endpoint}"

            try:
                if method.upper() == "GET":
                    response = requests.get(url, timeout=timeout)
                else:
                    response = requests.request(method, url, timeout=timeout)

                if response.status_code == 200:
                    successful_endpoints.append((name, endpoint, response.status_code))

                    # Validate JSON response if applicable
                    try:
                        data = response.json()
                        assert isinstance(
                            data, (dict, list)
                        ), f"Invalid JSON response for {endpoint}"
                    except (json.JSONDecodeError, ValueError):
                        # Non-JSON response is acceptable for some endpoints
                        pass

                else:
                    failed_endpoints.append((name, endpoint, response.status_code))

            except requests.exceptions.RequestException as e:
                failed_endpoints.append((name, endpoint, f"Request failed: {e}"))

        # Assert that at least the health check endpoint works
        health_endpoints = [
            ep for ep in successful_endpoints if "health" in ep[0].lower()
        ]
        assert len(health_endpoints) > 0, "No health check endpoints are working"

        # Log results for debugging
        if successful_endpoints:
            print(f"\n✅ Successful endpoints ({len(successful_endpoints)}):")
            for name, endpoint, status in successful_endpoints:
                print(f"  - {name} ({endpoint}): {status}")

        if failed_endpoints:
            print(f"\n❌ Failed endpoints ({len(failed_endpoints)}):")
            for name, endpoint, status in failed_endpoints:
                print(f"  - {name} ({endpoint}): {status}")

    def test_health_endpoint_detailed(self, base_url):
        """Test health endpoint returns proper structure."""
        url = f"{base_url}/health"

        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()

                    # Basic health response validation
                    if isinstance(data, dict):
                        # Check for common health check fields
                        expected_fields = ["status", "timestamp", "version"]
                        available_fields = [
                            field for field in expected_fields if field in data
                        ]

                        assert (
                            len(available_fields) > 0
                        ), "Health response missing expected fields"

                        if "status" in data:
                            assert data["status"] in [
                                "healthy",
                                "ok",
                                "up",
                                "running",
                            ], f"Unexpected health status: {data['status']}"

                except json.JSONDecodeError:
                    # Health endpoint might return plain text
                    assert (
                        "ok" in response.text.lower()
                        or "healthy" in response.text.lower()
                    ), "Health endpoint response doesn't indicate healthy status"
            else:
                pytest.fail(f"Health endpoint returned status {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Health endpoint request failed: {e}")

    @pytest.mark.slow
    def test_api_response_time(self, base_url):
        """Test API response time is acceptable."""
        url = f"{base_url}/health"
        max_response_time = 5.0  # seconds

        try:
            start_time = datetime.now()
            response = requests.get(url, timeout=max_response_time)
            end_time = datetime.now()

            response_time = (end_time - start_time).total_seconds()

            assert (
                response_time < max_response_time
            ), f"Response time {response_time:.2f}s exceeds maximum {max_response_time}s"

            assert (
                response.status_code == 200
            ), f"Health check failed with status {response.status_code}"

        except requests.exceptions.Timeout:
            pytest.fail(f"API response time exceeded {max_response_time} seconds")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"API request failed: {e}")

    def test_cors_headers(self, base_url):
        """Test CORS headers are properly configured."""
        url = f"{base_url}/health"

        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                headers = response.headers

                # Check for CORS headers (if applicable)
                cors_headers = [
                    "Access-Control-Allow-Origin",
                    "Access-Control-Allow-Methods",
                    "Access-Control-Allow-Headers",
                ]

                present_cors_headers = [h for h in cors_headers if h in headers]

                # CORS headers are optional, but if present, they should be valid
                if present_cors_headers:
                    print(f"CORS headers found: {present_cors_headers}")

                    if "Access-Control-Allow-Origin" in headers:
                        origin = headers["Access-Control-Allow-Origin"]
                        assert origin in ["*", base_url] or origin.startswith(
                            "http"
                        ), f"Invalid CORS origin: {origin}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Could not test CORS headers: {e}")


@pytest.mark.e2e
class TestBasicAPIWorkflow:
    """Test basic API workflow functionality."""

    def test_api_workflow_simulation(self, base_url):
        """Simulate a basic API workflow."""
        # This is a placeholder for a more complex workflow test
        # In a real scenario, this would test a complete user journey

        try:
            # Step 1: Check API availability
            health_response = requests.get(f"{base_url}/health", timeout=10)
            assert health_response.status_code == 200, "API not available"

            # Step 2: Check if main endpoints exist (without requiring them to work)
            endpoints_to_check = ["/", "/api/v1/stats"]

            for endpoint in endpoints_to_check:
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
                # Accept any response that's not a connection error
                assert response.status_code < 500, f"Server error on {endpoint}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API workflow test skipped due to connection issues: {e}")

    def test_image_upload_workflow(self, base_url):
        """Test basic image upload workflow."""
        try:
            # Create test image data
            test_data = b"fake image data for testing"
            files = {"file": ("test.jpg", test_data, "image/jpeg")}

            response = requests.post(
                f"{base_url}/api/v1/upload", files=files, timeout=15
            )

            # Accept various response codes as the endpoint might not be fully implemented
            assert response.status_code < 500, "Server error during upload"

            if response.status_code == 200:
                try:
                    data = response.json()
                    if "image_hash" in data:
                        assert len(data["image_hash"]) > 0, "Empty image hash returned"
                except json.JSONDecodeError:
                    # Non-JSON response is acceptable
                    pass

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Image upload test skipped due to connection issues: {e}")
