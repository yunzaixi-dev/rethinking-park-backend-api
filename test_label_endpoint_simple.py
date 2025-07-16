#!/usr/bin/env python3
"""
Simple test for the label-based analysis endpoint
Tests the endpoint logic without full application startup
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.image import LabelAnalysisRequest, LabelAnalysisResponse, LabelAnalysisResult, LabelCategoryResult
from services.label_analysis_service import label_analysis_service

def test_endpoint_logic():
    """Test the core endpoint logic"""
    print("🧪 Testing Label Analysis Endpoint Logic...")
    
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
        {"name": "Path", "confidence": 0.52, "topicality": 0.50}
    ]
    
    # Simulate the endpoint logic
    start_time = datetime.now()
    image_hash = "test_hash_123"
    target_categories = ["Plant", "Tree", "Sky", "Building"]
    confidence_threshold = 0.3
    max_labels = 50
    
    # Filter labels by confidence threshold
    filtered_labels = [
        label for label in mock_labels 
        if label.get("confidence", 0) >= confidence_threshold
    ][:max_labels]
    
    print(f"📊 Filtered {len(filtered_labels)} labels from {len(mock_labels)} total")
    
    # Perform label-based analysis
    analysis_result = label_analysis_service.analyze_by_labels(
        labels=filtered_labels,
        analysis_depth="comprehensive",
        include_confidence=True
    )
    
    # Create category results for target categories
    category_results = []
    categorized_elements = analysis_result.get("categorized_elements", {})
    
    for target_category in target_categories:
        category_key = target_category.lower()
        # Map common category names to our internal categories
        if category_key in ["plant", "tree", "grass", "flower"]:
            category_key = "vegetation"
        elif category_key in ["building", "structure"]:
            category_key = "built_environment"
        
        matched_labels = categorized_elements.get(category_key, [])
        
        if matched_labels:
            total_confidence = sum(label.get("confidence", 0) for label in matched_labels)
            average_confidence = total_confidence / len(matched_labels)
            coverage_estimate = min(100.0, total_confidence * 20)  # Simple coverage estimation
            
            category_result = LabelCategoryResult(
                category_name=target_category,
                matched_labels=matched_labels,
                total_confidence=total_confidence,
                average_confidence=average_confidence,
                coverage_estimate=coverage_estimate,
                label_count=len(matched_labels)
            )
            category_results.append(category_result)
    
    # Extract coverage statistics
    coverage_stats = analysis_result.get("coverage_statistics", {})
    natural_elements_summary = {
        "vegetation": coverage_stats.get("vegetation_coverage", 0.0),
        "sky": coverage_stats.get("sky_coverage", 0.0),
        "water": coverage_stats.get("water_coverage", 0.0),
        "built_environment": coverage_stats.get("built_environment_coverage", 0.0)
    }
    
    # Create confidence distribution
    confidence_analysis = analysis_result.get("confidence_analysis", {})
    confidence_distribution = confidence_analysis.get("confidence_distribution", {
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0
    })
    
    # Get top categories
    top_categories = sorted(
        natural_elements_summary.items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:3]
    top_categories = [category for category, _ in top_categories if _ > 0]
    
    # Create analysis result
    result = LabelAnalysisResult(
        all_labels=filtered_labels,
        category_analysis=category_results,
        natural_elements_summary=natural_elements_summary,
        confidence_distribution=confidence_distribution,
        top_categories=top_categories,
        analysis_metadata={
            "total_labels_processed": len(filtered_labels),
            "confidence_threshold": confidence_threshold,
            "target_categories": target_categories,
            "analysis_time": datetime.now().isoformat()
        }
    )
    
    # Create response
    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
    response = LabelAnalysisResponse(
        image_hash=image_hash,
        results=result,
        processing_time_ms=processing_time,
        success=True,
        from_cache=False,
        error_message=None
    )
    
    print(f"✅ Endpoint logic completed successfully")
    print(f"📊 Categories analyzed: {len(response.results.category_analysis)}")
    print(f"⏱️ Processing time: {response.processing_time_ms}ms")
    print(f"🎯 Top categories: {response.results.top_categories}")
    
    # Validate response structure
    try:
        assert response.success == True, f"Expected success=True, got {response.success}"
        assert response.image_hash == image_hash, f"Expected hash {image_hash}, got {response.image_hash}"
        assert len(response.results.category_analysis) > 0, f"Expected categories > 0, got {len(response.results.category_analysis)}"
        assert response.processing_time_ms >= 0, f"Expected processing_time >= 0, got {response.processing_time_ms}"
    except AssertionError as e:
        print(f"❌ Validation failed: {e}")
        return False
    
    # Print detailed results
    print("\n📋 Category Analysis Results:")
    for category in response.results.category_analysis:
        print(f"  🏷️ {category.category_name}:")
        print(f"    - Labels: {category.label_count}")
        print(f"    - Coverage: {category.coverage_estimate:.1f}%")
        print(f"    - Avg Confidence: {category.average_confidence:.2f}")
    
    print("\n🌿 Natural Elements Summary:")
    for element, coverage in response.results.natural_elements_summary.items():
        if coverage > 0:
            print(f"  - {element.title()}: {coverage:.1f}%")
    
    return True

def test_request_response_models():
    """Test the request and response models"""
    print("\n🧪 Testing Request/Response Models...")
    
    # Test request model
    request = LabelAnalysisRequest(
        image_hash="test_hash_456",
        target_categories=["Plant", "Sky", "Water"],
        include_confidence=True,
        confidence_threshold=0.4,
        max_labels=25
    )
    
    print(f"✅ Request model created: {request.image_hash}")
    print(f"📋 Categories: {request.target_categories}")
    print(f"🎯 Threshold: {request.confidence_threshold}")
    
    # Test response model with mock data
    mock_category = LabelCategoryResult(
        category_name="Plant",
        matched_labels=[{"name": "Tree", "confidence": 0.9}],
        total_confidence=0.9,
        average_confidence=0.9,
        coverage_estimate=18.0,
        label_count=1
    )
    
    mock_result = LabelAnalysisResult(
        all_labels=[{"name": "Tree", "confidence": 0.9}],
        category_analysis=[mock_category],
        natural_elements_summary={"vegetation": 18.0},
        confidence_distribution={"high_confidence": 1, "medium_confidence": 0, "low_confidence": 0},
        top_categories=["vegetation"],
        analysis_metadata={"total_labels_processed": 1}
    )
    
    response = LabelAnalysisResponse(
        image_hash="test_hash_456",
        results=mock_result,
        processing_time_ms=150,
        success=True,
        from_cache=False
    )
    
    print(f"✅ Response model created successfully")
    print(f"📊 Success: {response.success}")
    print(f"⏱️ Processing time: {response.processing_time_ms}ms")
    
    return True

def test_error_handling():
    """Test error handling in the endpoint logic"""
    print("\n🧪 Testing Error Handling...")
    
    # Test with empty labels
    try:
        result = label_analysis_service.analyze_by_labels(
            labels=[],
            analysis_depth="basic",
            include_confidence=True
        )
        
        # Should handle empty labels gracefully
        assert "categorized_elements" in result
        print("✅ Empty labels handled gracefully")
        
    except Exception as e:
        print(f"❌ Error handling empty labels failed: {e}")
        return False
    
    # Test with invalid labels
    try:
        invalid_labels = [
            {"invalid_field": "test"},  # Missing required fields
            {"name": "Tree"}  # Missing confidence
        ]
        
        result = label_analysis_service.analyze_by_labels(
            labels=invalid_labels,
            analysis_depth="basic",
            include_confidence=True
        )
        
        # Should handle invalid labels gracefully
        assert "categorized_elements" in result
        print("✅ Invalid labels handled gracefully")
        
    except Exception as e:
        print(f"❌ Error handling invalid labels failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Label Analysis Endpoint Simple Tests")
    print("=" * 55)
    
    tests = [
        ("Endpoint Logic", test_endpoint_logic),
        ("Request/Response Models", test_request_response_models),
        ("Error Handling", test_error_handling)
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
        
        print("-" * 35)
    
    # Summary
    print("\n📊 Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Label analysis endpoint implementation is correct.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)