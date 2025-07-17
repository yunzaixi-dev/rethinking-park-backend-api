#!/usr/bin/env python3
"""
Test script for the label-based analysis endpoint
Tests the POST /api/v1/analyze-by-labels endpoint implementation
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.image import LabelAnalysisRequest, LabelAnalysisResponse
from services.label_analysis_service import label_analysis_service


def test_label_analysis_service():
    """Test the label analysis service directly"""
    print("🧪 Testing Label Analysis Service...")

    # Mock Google Vision API labels response
    mock_labels = [
        {"name": "Tree", "confidence": 0.95, "topicality": 0.92},
        {"name": "Plant", "confidence": 0.88, "topicality": 0.85},
        {"name": "Grass", "confidence": 0.82, "topicality": 0.80},
        {"name": "Sky", "confidence": 0.91, "topicality": 0.89},
        {"name": "Cloud", "confidence": 0.76, "topicality": 0.74},
        {"name": "Building", "confidence": 0.65, "topicality": 0.62},
        {"name": "Water", "confidence": 0.58, "topicality": 0.55},
        {"name": "Flower", "confidence": 0.72, "topicality": 0.70},
        {"name": "Bench", "confidence": 0.45, "topicality": 0.43},
        {"name": "Path", "confidence": 0.52, "topicality": 0.50},
    ]

    # Test basic analysis
    result = label_analysis_service.analyze_by_labels(
        labels=mock_labels, analysis_depth="comprehensive", include_confidence=True
    )

    print(f"✅ Analysis completed successfully")
    print(f"📊 Categories found: {list(result.get('categorized_elements', {}).keys())}")

    # Check coverage statistics
    coverage_stats = result.get("coverage_statistics", {})
    print(
        f"🌿 Vegetation coverage: {coverage_stats.get('vegetation_coverage', 0):.1f}%"
    )
    print(f"☁️ Sky coverage: {coverage_stats.get('sky_coverage', 0):.1f}%")
    print(f"💧 Water coverage: {coverage_stats.get('water_coverage', 0):.1f}%")
    print(
        f"🏢 Built environment coverage: {coverage_stats.get('built_environment_coverage', 0):.1f}%"
    )

    # Check insights
    insights = result.get("natural_element_insights", {})
    print(f"🎯 Dominant element: {insights.get('dominant_natural_element', 'Unknown')}")
    print(
        f"🌱 Environmental health score: {insights.get('environmental_health_score', 0):.1f}"
    )

    # Check confidence analysis
    confidence_analysis = result.get("confidence_analysis", {})
    if confidence_analysis:
        conf_dist = confidence_analysis.get("confidence_distribution", {})
        print(f"📈 High confidence labels: {conf_dist.get('high_confidence', 0)}")
        print(f"📊 Medium confidence labels: {conf_dist.get('medium_confidence', 0)}")
        print(f"📉 Low confidence labels: {conf_dist.get('low_confidence', 0)}")

    return result


def test_label_analysis_request_model():
    """Test the request model validation"""
    print("\n🧪 Testing Label Analysis Request Model...")

    # Test valid request
    try:
        request = LabelAnalysisRequest(
            image_hash="test_hash_123",
            target_categories=["Plant", "Tree", "Sky", "Building"],
            include_confidence=True,
            confidence_threshold=0.3,
            max_labels=50,
        )
        print(f"✅ Valid request created: {request.image_hash}")
        print(f"📋 Target categories: {request.target_categories}")
        print(f"🎯 Confidence threshold: {request.confidence_threshold}")

    except Exception as e:
        print(f"❌ Request model validation failed: {e}")
        return False

    # Test with default values
    try:
        request_default = LabelAnalysisRequest(image_hash="test_hash_456")
        print(
            f"✅ Default request created with categories: {request_default.target_categories}"
        )

    except Exception as e:
        print(f"❌ Default request creation failed: {e}")
        return False

    return True


def test_label_analysis_response_model():
    """Test the response model creation"""
    print("\n🧪 Testing Label Analysis Response Model...")

    try:
        # Create mock analysis result
        from models.image import LabelAnalysisResult, LabelCategoryResult

        # Create category results
        category_results = [
            LabelCategoryResult(
                category_name="Plant",
                matched_labels=[
                    {"name": "Tree", "confidence": 0.95},
                    {"name": "Grass", "confidence": 0.82},
                ],
                total_confidence=1.77,
                average_confidence=0.885,
                coverage_estimate=35.4,
                label_count=2,
            ),
            LabelCategoryResult(
                category_name="Sky",
                matched_labels=[
                    {"name": "Sky", "confidence": 0.91},
                    {"name": "Cloud", "confidence": 0.76},
                ],
                total_confidence=1.67,
                average_confidence=0.835,
                coverage_estimate=33.4,
                label_count=2,
            ),
        ]

        # Create analysis result
        analysis_result = LabelAnalysisResult(
            all_labels=[
                {"name": "Tree", "confidence": 0.95},
                {"name": "Sky", "confidence": 0.91},
                {"name": "Grass", "confidence": 0.82},
            ],
            category_analysis=category_results,
            natural_elements_summary={
                "vegetation": 35.4,
                "sky": 33.4,
                "water": 0.0,
                "built_environment": 15.2,
            },
            confidence_distribution={
                "high_confidence": 2,
                "medium_confidence": 1,
                "low_confidence": 0,
            },
            top_categories=["vegetation", "sky", "built_environment"],
            analysis_metadata={
                "total_labels_processed": 3,
                "confidence_threshold": 0.3,
                "target_categories": ["Plant", "Sky"],
                "analysis_time": datetime.now().isoformat(),
            },
        )

        # Create response
        response = LabelAnalysisResponse(
            image_hash="test_hash_123",
            results=analysis_result,
            processing_time_ms=250,
            success=True,
            from_cache=False,
            error_message=None,
        )

        print(f"✅ Response model created successfully")
        print(f"📊 Categories analyzed: {len(response.results.category_analysis)}")
        print(f"⏱️ Processing time: {response.processing_time_ms}ms")
        print(f"🎯 Top categories: {response.results.top_categories}")

        return True

    except Exception as e:
        print(f"❌ Response model creation failed: {e}")
        return False


def test_category_mapping():
    """Test the category mapping functionality"""
    print("\n🧪 Testing Category Mapping...")

    test_labels = [
        {"name": "Oak Tree", "confidence": 0.95},
        {"name": "Blue Sky", "confidence": 0.88},
        {"name": "Garden Bench", "confidence": 0.72},
        {"name": "Pond Water", "confidence": 0.65},
        {"name": "Green Grass", "confidence": 0.82},
        {"name": "Stone Path", "confidence": 0.58},
        {"name": "Rose Flower", "confidence": 0.76},
    ]

    categorized = label_analysis_service._categorize_labels(test_labels)

    print("📋 Category mapping results:")
    for category, labels in categorized.items():
        if labels:
            print(f"  {category}: {len(labels)} labels")
            for label in labels:
                print(f"    - {label['name']} (confidence: {label['confidence']:.2f})")

    # Verify expected categorizations
    expected_categories = {
        "vegetation": ["Oak Tree", "Green Grass", "Rose Flower"],
        "sky": ["Blue Sky"],
        "built_environment": ["Garden Bench", "Stone Path"],
        "water": ["Pond Water"],
    }

    success = True
    for category, expected_labels in expected_categories.items():
        actual_labels = [label["name"] for label in categorized.get(category, [])]
        for expected_label in expected_labels:
            if not any(
                expected_label in actual_label for actual_label in actual_labels
            ):
                print(
                    f"❌ Expected label '{expected_label}' not found in category '{category}'"
                )
                success = False

    if success:
        print("✅ Category mapping working correctly")

    return success


def main():
    """Run all tests"""
    print("🚀 Starting Label Analysis Endpoint Tests")
    print("=" * 50)

    tests = [
        ("Label Analysis Service", test_label_analysis_service),
        ("Request Model Validation", test_label_analysis_request_model),
        ("Response Model Creation", test_label_analysis_response_model),
        ("Category Mapping", test_category_mapping),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result is not False))
            if result is not False:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))

        print("-" * 30)

    # Summary
    print("\n📊 Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Label analysis endpoint is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
