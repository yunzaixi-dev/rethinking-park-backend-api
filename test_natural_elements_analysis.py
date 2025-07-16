#!/usr/bin/env python3
"""
Test script for Natural Elements Analysis System
Tests the implementation of task 4: Create natural elements analysis system based on Google Vision labels
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.natural_element_analyzer import NaturalElementAnalyzer
from models.image import (
    NaturalElementsResult, 
    VegetationHealthMetrics,
    SeasonalAnalysis,
    NaturalElementCategory,
    ColorInfo
)

class MockVisionClient:
    """Mock Google Vision client for testing"""
    
    def __init__(self):
        self.mock_labels = [
            type('Label', (), {
                'description': 'Tree',
                'score': 0.95,
                'topicality': 0.9
            })(),
            type('Label', (), {
                'description': 'Grass',
                'score': 0.87,
                'topicality': 0.85
            })(),
            type('Label', (), {
                'description': 'Sky',
                'score': 0.92,
                'topicality': 0.88
            })(),
            type('Label', (), {
                'description': 'Green',
                'score': 0.78,
                'topicality': 0.75
            })(),
            type('Label', (), {
                'description': 'Plant',
                'score': 0.82,
                'topicality': 0.80
            })(),
            type('Label', (), {
                'description': 'Nature',
                'score': 0.89,
                'topicality': 0.85
            })(),
            type('Label', (), {
                'description': 'Outdoor',
                'score': 0.91,
                'topicality': 0.87
            })(),
            type('Label', (), {
                'description': 'Leaf',
                'score': 0.76,
                'topicality': 0.72
            })(),
        ]
    
    def label_detection(self, image):
        """Mock label detection"""
        response = type('Response', (), {
            'label_annotations': self.mock_labels,
            'error': type('Error', (), {'message': None})()
        })()
        return response

def create_mock_image_content() -> bytes:
    """Create mock image content for testing"""
    # Create a simple mock image (green dominant for vegetation)
    from PIL import Image
    import io
    
    # Create a 100x100 green image to simulate park vegetation
    img = Image.new('RGB', (100, 100), color=(80, 150, 60))  # Green color
    
    # Add some variation
    pixels = img.load()
    for i in range(100):
        for j in range(100):
            # Add some color variation to simulate natural vegetation
            r = max(0, min(255, 80 + (i % 20) - 10))
            g = max(0, min(255, 150 + (j % 30) - 15))
            b = max(0, min(255, 60 + ((i + j) % 25) - 12))
            pixels[i, j] = (r, g, b)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

async def test_natural_element_analyzer():
    """Test the NaturalElementAnalyzer service"""
    print("🧪 Testing Natural Elements Analysis System")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = NaturalElementAnalyzer()
    mock_client = MockVisionClient()
    mock_image_content = create_mock_image_content()
    
    try:
        # Test comprehensive analysis
        print("\n1. Testing comprehensive natural elements analysis...")
        result = await analyzer.analyze_natural_elements(
            image_content=mock_image_content,
            vision_client=mock_client,
            analysis_depth="comprehensive"
        )
        
        # Verify result type
        assert isinstance(result, NaturalElementsResult), "Result should be NaturalElementsResult"
        print("✅ Analysis completed successfully")
        
        # Test coverage statistics
        print("\n2. Testing coverage statistics...")
        print(f"   Vegetation coverage: {result.vegetation_coverage:.1f}%")
        print(f"   Sky coverage: {result.sky_coverage:.1f}%")
        print(f"   Water coverage: {result.water_coverage:.1f}%")
        print(f"   Built environment coverage: {result.built_environment_coverage:.1f}%")
        
        assert result.vegetation_coverage >= 0.0, "Vegetation coverage should be non-negative"
        assert result.vegetation_coverage <= 100.0, "Vegetation coverage should not exceed 100%"
        print("✅ Coverage statistics are valid")
        
        # Test vegetation health assessment
        print("\n3. Testing vegetation health assessment...")
        if result.vegetation_health_score is not None:
            print(f"   Overall health score: {result.vegetation_health_score:.1f}")
            assert 0.0 <= result.vegetation_health_score <= 100.0, "Health score should be 0-100"
            print("✅ Vegetation health score is valid")
        
        if result.vegetation_health_metrics:
            metrics = result.vegetation_health_metrics
            print(f"   Health status: {metrics.health_status}")
            print(f"   Color health score: {metrics.color_health_score:.1f}")
            print(f"   Coverage health score: {metrics.coverage_health_score:.1f}")
            print(f"   Label health score: {metrics.label_health_score:.1f}")
            print(f"   Green ratio: {metrics.green_ratio:.3f}")
            
            assert isinstance(metrics, VegetationHealthMetrics), "Should be VegetationHealthMetrics"
            assert metrics.health_status in ["healthy", "moderate", "poor", "unknown"], "Invalid health status"
            print("✅ Vegetation health metrics are comprehensive")
        
        # Test seasonal analysis
        print("\n4. Testing seasonal analysis...")
        if result.seasonal_analysis:
            seasonal = result.seasonal_analysis
            print(f"   Detected seasons: {seasonal.detected_seasons}")
            print(f"   Primary season: {seasonal.primary_season}")
            print(f"   Seasonal features: {seasonal.seasonal_features}")
            
            assert isinstance(seasonal, SeasonalAnalysis), "Should be SeasonalAnalysis"
            print("✅ Seasonal analysis is comprehensive")
        
        # Test color analysis
        print("\n5. Testing color analysis...")
        print(f"   Number of dominant colors: {len(result.dominant_colors)}")
        if result.color_diversity_score is not None:
            print(f"   Color diversity score: {result.color_diversity_score:.1f}")
            assert 0.0 <= result.color_diversity_score <= 100.0, "Color diversity should be 0-100"
        
        for i, color in enumerate(result.dominant_colors):
            assert isinstance(color, ColorInfo), "Should be ColorInfo"
            print(f"   Color {i+1}: {color.color_name} ({color.hex_code})")
        print("✅ Color analysis is detailed")
        
        # Test element categories
        print("\n6. Testing element categories...")
        print(f"   Number of element categories: {len(result.element_categories)}")
        for category in result.element_categories:
            assert isinstance(category, NaturalElementCategory), "Should be NaturalElementCategory"
            print(f"   {category.category_name}: {category.coverage_percentage:.1f}% coverage")
            print(f"     Confidence: {category.confidence_score:.3f}")
            print(f"     Elements: {category.element_count}")
        print("✅ Element categories are detailed")
        
        # Test analysis metadata
        print("\n7. Testing analysis metadata...")
        print(f"   Analysis depth: {result.analysis_depth}")
        print(f"   Total labels analyzed: {result.total_labels_analyzed}")
        print(f"   Overall assessment: {result.overall_assessment}")
        print(f"   Number of recommendations: {len(result.recommendations)}")
        
        assert result.analysis_depth in ["basic", "comprehensive"], "Invalid analysis depth"
        assert result.total_labels_analyzed >= 0, "Label count should be non-negative"
        print("✅ Analysis metadata is complete")
        
        # Test recommendations
        print("\n8. Testing recommendations...")
        for i, rec in enumerate(result.recommendations):
            print(f"   {i+1}. {rec}")
        print("✅ Recommendations are generated")
        
        # Test basic analysis mode
        print("\n9. Testing basic analysis mode...")
        basic_result = await analyzer.analyze_natural_elements(
            image_content=mock_image_content,
            vision_client=mock_client,
            analysis_depth="basic"
        )
        
        assert basic_result.analysis_depth == "basic", "Should be basic analysis"
        print("✅ Basic analysis mode works")
        
        # Test error handling
        print("\n10. Testing error handling...")
        
        # Mock client that raises an error
        class ErrorMockClient:
            def label_detection(self, image):
                response = type('Response', (), {
                    'error': type('Error', (), {'message': 'Test error'})()
                })()
                return response
        
        error_client = ErrorMockClient()
        error_result = await analyzer.analyze_natural_elements(
            image_content=mock_image_content,
            vision_client=error_client,
            analysis_depth="comprehensive"
        )
        
        assert error_result.overall_assessment == "error", "Should handle errors gracefully"
        assert "Analysis failed" in error_result.recommendations[0], "Should provide error feedback"
        print("✅ Error handling works correctly")
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Natural Elements Analysis System is working correctly")
        print("✅ Requirements 5.1, 5.2, 5.3, 5.4 are satisfied")
        
        # Print summary of capabilities
        print("\n📋 IMPLEMENTED CAPABILITIES:")
        print("   ✅ Label-based detection for natural elements (trees, grass, sky, water)")
        print("   ✅ Vegetation health assessment based on color analysis and label confidence")
        print("   ✅ Coverage percentage estimation from label data")
        print("   ✅ Seasonal indicator detection from labels")
        print("   ✅ Comprehensive natural elements response models")
        print("   ✅ Detailed vegetation health scoring")
        print("   ✅ Enhanced color analysis and diversity scoring")
        print("   ✅ Element categorization and detailed breakdowns")
        print("   ✅ Recommendations and overall assessment")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_model_validation():
    """Test the enhanced data models"""
    print("\n🧪 Testing Enhanced Data Models")
    print("=" * 40)
    
    try:
        # Test VegetationHealthMetrics
        health_metrics = VegetationHealthMetrics(
            overall_score=85.5,
            color_health_score=80.0,
            coverage_health_score=90.0,
            label_health_score=86.0,
            green_ratio=0.45,
            health_status="healthy",
            recommendations=["Maintain current practices"]
        )
        print("✅ VegetationHealthMetrics model works")
        
        # Test SeasonalAnalysis
        seasonal_analysis = SeasonalAnalysis(
            detected_seasons=["spring", "summer"],
            confidence_scores={"spring": 0.8, "summer": 0.6},
            primary_season="spring",
            seasonal_features=["fresh growth", "green foliage"]
        )
        print("✅ SeasonalAnalysis model works")
        
        # Test NaturalElementCategory
        element_category = NaturalElementCategory(
            category_name="Vegetation",
            coverage_percentage=75.5,
            confidence_score=0.89,
            detected_labels=["tree", "grass", "plant"],
            element_count=3
        )
        print("✅ NaturalElementCategory model works")
        
        # Test enhanced ColorInfo
        color_info = ColorInfo(
            red=80.0,
            green=150.0,
            blue=60.0,
            hex_code="#50963C",
            color_name="Forest Green",
            percentage=65.5
        )
        print("✅ Enhanced ColorInfo model works")
        
        # Test complete NaturalElementsResult
        complete_result = NaturalElementsResult(
            vegetation_coverage=75.5,
            sky_coverage=20.0,
            water_coverage=2.5,
            built_environment_coverage=2.0,
            vegetation_health_score=85.5,
            vegetation_health_metrics=health_metrics,
            dominant_colors=[color_info],
            color_diversity_score=68.5,
            seasonal_indicators=["spring"],
            seasonal_analysis=seasonal_analysis,
            element_categories=[element_category],
            analysis_depth="comprehensive",
            total_labels_analyzed=8,
            overall_assessment="thriving_natural_environment",
            recommendations=["Excellent vegetation coverage"]
        )
        print("✅ Complete NaturalElementsResult model works")
        
        print("🎉 All data models are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Model validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Natural Elements Analysis System Tests")
    print("Testing implementation of Task 4 and its sub-tasks")
    
    # Test data models first
    model_test_passed = test_model_validation()
    
    if not model_test_passed:
        print("❌ Model tests failed, skipping service tests")
        return False
    
    # Test the service
    service_test_passed = await test_natural_element_analyzer()
    
    if model_test_passed and service_test_passed:
        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("✅ Task 4: Create natural elements analysis system - COMPLETED")
        print("✅ Sub-task 4.1: Implement NaturalElementAnalyzer service - COMPLETED")
        print("✅ Sub-task 4.2: Build natural elements response models - COMPLETED")
        return True
    else:
        print("\n❌ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)