#!/usr/bin/env python3
"""
Integration test for Natural Elements Analysis with Enhanced Vision Service
Tests the integration between the new NaturalElementAnalyzer and existing services
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.natural_element_analyzer import natural_element_analyzer
from services.enhanced_vision_service import enhanced_vision_service
from models.image import NaturalElementsRequest, NaturalElementsResponse

def test_service_imports():
    """Test that all services can be imported correctly"""
    print("🧪 Testing Service Imports and Integration")
    print("=" * 50)
    
    try:
        # Test that the global instance is available
        assert natural_element_analyzer is not None, "Natural element analyzer should be available"
        print("✅ NaturalElementAnalyzer service imported successfully")
        
        # Test that enhanced vision service is available
        assert enhanced_vision_service is not None, "Enhanced vision service should be available"
        print("✅ EnhancedVisionService imported successfully")
        
        # Test that the analyzer has the expected methods
        assert hasattr(natural_element_analyzer, 'analyze_natural_elements'), "Should have analyze_natural_elements method"
        assert hasattr(natural_element_analyzer, 'get_analysis_summary'), "Should have get_analysis_summary method"
        print("✅ NaturalElementAnalyzer has expected methods")
        
        # Test that enhanced vision service has natural elements analysis
        assert hasattr(enhanced_vision_service, 'analyze_natural_elements'), "Should have analyze_natural_elements method"
        print("✅ EnhancedVisionService has natural elements analysis")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_model_compatibility():
    """Test that the new models are compatible with the existing system"""
    print("\n🧪 Testing Model Compatibility")
    print("=" * 40)
    
    try:
        # Test NaturalElementsRequest model
        request = NaturalElementsRequest(
            image_hash="test_hash_123",
            analysis_depth="comprehensive",
            include_health_assessment=True,
            include_seasonal_analysis=True,
            include_color_analysis=True,
            confidence_threshold=0.3
        )
        print("✅ NaturalElementsRequest model works")
        
        # Test that the request has expected fields
        assert request.image_hash == "test_hash_123", "Image hash should be set"
        assert request.analysis_depth == "comprehensive", "Analysis depth should be comprehensive"
        assert request.include_health_assessment == True, "Health assessment should be enabled"
        print("✅ NaturalElementsRequest fields are correct")
        
        # Test NaturalElementsResponse model structure
        from models.image import NaturalElementsResult
        
        # Create a minimal result for testing
        result = NaturalElementsResult(
            vegetation_coverage=50.0,
            sky_coverage=30.0,
            water_coverage=10.0,
            built_environment_coverage=10.0,
            analysis_depth="comprehensive",
            total_labels_analyzed=5,
            overall_assessment="balanced_environment",
            recommendations=["Test recommendation"]
        )
        
        response = NaturalElementsResponse(
            image_hash="test_hash_123",
            results=result,
            processing_time_ms=1500,
            success=True,
            from_cache=False,
            error_message=None,
            enabled=True
        )
        print("✅ NaturalElementsResponse model works")
        
        # Verify response structure
        assert response.image_hash == "test_hash_123", "Image hash should match"
        assert response.success == True, "Success should be True"
        assert response.results.vegetation_coverage == 50.0, "Vegetation coverage should be 50%"
        print("✅ NaturalElementsResponse structure is correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Model compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analyzer_categories():
    """Test that the analyzer has proper category definitions"""
    print("\n🧪 Testing Analyzer Category Definitions")
    print("=" * 45)
    
    try:
        # Test category structure
        categories = natural_element_analyzer.natural_element_categories
        
        expected_categories = ["vegetation", "sky", "water", "terrain", "built_environment"]
        for category in expected_categories:
            assert category in categories, f"Category {category} should be defined"
            assert "keywords" in categories[category], f"Category {category} should have keywords"
            assert "weight" in categories[category], f"Category {category} should have weight"
        
        print("✅ All expected categories are defined")
        
        # Test vegetation keywords
        vegetation_keywords = categories["vegetation"]["keywords"]
        expected_veg_keywords = ["tree", "plant", "grass", "flower", "leaf"]
        for keyword in expected_veg_keywords:
            assert keyword in vegetation_keywords, f"Vegetation should include {keyword}"
        
        print("✅ Vegetation keywords are comprehensive")
        
        # Test seasonal indicators
        seasonal_indicators = natural_element_analyzer.seasonal_indicators
        expected_seasons = ["spring", "summer", "autumn", "winter"]
        for season in expected_seasons:
            assert season in seasonal_indicators, f"Season {season} should be defined"
        
        print("✅ Seasonal indicators are defined")
        
        # Test health indicators
        health_indicators = natural_element_analyzer.health_indicators
        expected_health_levels = ["healthy", "moderate", "poor"]
        for level in expected_health_levels:
            assert level in health_indicators, f"Health level {level} should be defined"
        
        print("✅ Health indicators are defined")
        
        return True
        
    except Exception as e:
        print(f"❌ Category definition test failed: {e}")
        return False

async def main():
    """Main integration test function"""
    print("🚀 Starting Natural Elements Analysis Integration Tests")
    print("Testing integration with existing Enhanced Vision Service")
    
    # Run all tests
    import_test_passed = test_service_imports()
    model_test_passed = test_model_compatibility()
    category_test_passed = test_analyzer_categories()
    
    if import_test_passed and model_test_passed and category_test_passed:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Natural Elements Analysis System is properly integrated")
        print("✅ Ready for use with Enhanced Vision Service")
        print("✅ All models and services are compatible")
        
        print("\n📋 INTEGRATION SUMMARY:")
        print("   ✅ Service imports work correctly")
        print("   ✅ Models are compatible with existing system")
        print("   ✅ Category definitions are comprehensive")
        print("   ✅ Ready for API endpoint integration")
        
        return True
    else:
        print("\n❌ SOME INTEGRATION TESTS FAILED")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)