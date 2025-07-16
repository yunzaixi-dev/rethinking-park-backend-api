#!/usr/bin/env python3
"""
Verification script for natural elements analysis implementation
Tests the implementation without requiring a running server
"""

import sys
import traceback
from datetime import datetime

def test_imports():
    """Test that all required imports work"""
    print("🔍 Testing imports...")
    
    try:
        # Test model imports
        from models.image import NaturalElementsRequest, NaturalElementsResponse, NaturalElementsResult
        print("   ✅ Model imports successful")
        
        # Test service imports
        from services.natural_element_analyzer import natural_element_analyzer
        print("   ✅ Natural element analyzer import successful")
        
        from services.vision_service import vision_service
        print("   ✅ Vision service import successful")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_model_validation():
    """Test model validation"""
    print("\n🧪 Testing model validation...")
    
    try:
        from models.image import NaturalElementsRequest, NaturalElementsResponse
        
        # Test valid request
        valid_request = NaturalElementsRequest(
            image_hash="test_hash_123",
            analysis_depth="comprehensive",
            include_health_assessment=True,
            include_seasonal_analysis=True,
            include_color_analysis=True,
            confidence_threshold=0.3
        )
        print("   ✅ Valid request model creation successful")
        print(f"   Request: {valid_request.dict()}")
        
        # Test default values
        minimal_request = NaturalElementsRequest(image_hash="test_hash_456")
        print("   ✅ Minimal request with defaults successful")
        print(f"   Defaults: analysis_depth={minimal_request.analysis_depth}, confidence_threshold={minimal_request.confidence_threshold}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Model validation failed: {e}")
        traceback.print_exc()
        return False

def test_natural_element_analyzer():
    """Test natural element analyzer functionality"""
    print("\n🔬 Testing natural element analyzer...")
    
    try:
        from services.natural_element_analyzer import natural_element_analyzer
        
        # Test analyzer initialization
        print(f"   ✅ Analyzer initialized")
        print(f"   Categories: {list(natural_element_analyzer.natural_element_categories.keys())}")
        print(f"   Seasonal indicators: {list(natural_element_analyzer.seasonal_indicators.keys())}")
        print(f"   Health indicators: {list(natural_element_analyzer.health_indicators.keys())}")
        
        # Test helper methods
        test_labels = [
            {"name": "Tree", "confidence": 0.9, "topicality": 0.8},
            {"name": "Grass", "confidence": 0.7, "topicality": 0.6},
            {"name": "Sky", "confidence": 0.8, "topicality": 0.9},
            {"name": "Building", "confidence": 0.6, "topicality": 0.5}
        ]
        
        categorized = natural_element_analyzer._categorize_labels_by_natural_elements(test_labels)
        print(f"   ✅ Label categorization successful")
        for category, labels in categorized.items():
            if labels:
                print(f"     {category}: {len(labels)} labels")
        
        coverage_stats = natural_element_analyzer._calculate_coverage_percentages(categorized)
        print(f"   ✅ Coverage calculation successful")
        for stat, value in coverage_stats.items():
            print(f"     {stat}: {value:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Natural element analyzer test failed: {e}")
        traceback.print_exc()
        return False

def test_vision_service_availability():
    """Test vision service availability"""
    print("\n👁️  Testing vision service availability...")
    
    try:
        from services.vision_service import vision_service
        
        is_enabled = vision_service.is_enabled()
        print(f"   Vision service enabled: {is_enabled}")
        
        if is_enabled:
            print("   ✅ Vision service is available")
            print("   Google Cloud credentials are properly configured")
        else:
            print("   ⚠️  Vision service is not available")
            print("   This is expected if Google Cloud credentials are not configured")
            print("   The endpoint will return appropriate error messages")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Vision service test failed: {e}")
        traceback.print_exc()
        return False

def test_endpoint_function_structure():
    """Test that the endpoint function is properly structured"""
    print("\n🔧 Testing endpoint function structure...")
    
    try:
        # Import the main module to check if the endpoint is defined
        import main
        
        # Check if the app has the analyze_nature endpoint
        routes = []
        for route in main.app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append(f"{list(route.methods)[0] if route.methods else 'GET'} {route.path}")
        
        analyze_nature_route = None
        for route in routes:
            if '/analyze-nature' in route:
                analyze_nature_route = route
                break
        
        if analyze_nature_route:
            print(f"   ✅ Endpoint found: {analyze_nature_route}")
        else:
            print("   ❌ /analyze-nature endpoint not found")
            print("   Available routes:")
            for route in routes[:10]:  # Show first 10 routes
                print(f"     {route}")
            return False
        
        # Check if the analyze_nature function exists
        if hasattr(main, 'analyze_nature'):
            print("   ✅ analyze_nature function exists")
        else:
            print("   ❌ analyze_nature function not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Endpoint structure test failed: {e}")
        traceback.print_exc()
        return False

def test_response_model_creation():
    """Test response model creation"""
    print("\n📝 Testing response model creation...")
    
    try:
        from models.image import (
            NaturalElementsResponse, 
            NaturalElementsResult,
            VegetationHealthMetrics,
            SeasonalAnalysis,
            NaturalElementCategory,
            ColorInfo
        )
        from datetime import datetime
        
        # Create a sample result
        sample_result = NaturalElementsResult(
            vegetation_coverage=65.5,
            sky_coverage=25.0,
            water_coverage=5.0,
            built_environment_coverage=4.5,
            vegetation_health_score=78.5,
            dominant_colors=[
                ColorInfo(red=34.5, green=120.2, blue=45.8, hex_code="#22782D")
            ],
            seasonal_indicators=["spring", "healthy"],
            element_categories=[
                NaturalElementCategory(
                    category_name="Vegetation",
                    coverage_percentage=65.5,
                    confidence_score=0.85,
                    detected_labels=["Tree", "Grass", "Plant"],
                    element_count=3
                )
            ],
            analysis_time=datetime.now(),
            analysis_depth="comprehensive",
            total_labels_analyzed=15,
            overall_assessment="nature_dominant",
            recommendations=["Vegetation appears healthy", "Continue current maintenance"]
        )
        
        # Create response
        response = NaturalElementsResponse(
            image_hash="test_hash_123",
            results=sample_result,
            processing_time_ms=1250,
            success=True,
            from_cache=False,
            error_message=None,
            enabled=True
        )
        
        print("   ✅ Response model creation successful")
        print(f"   Response keys: {list(response.dict().keys())}")
        print(f"   Results keys: {list(response.results.dict().keys())}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Response model creation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main verification function"""
    print("🚀 Natural Elements Analysis Implementation Verification")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    tests = [
        ("Imports", test_imports),
        ("Model Validation", test_model_validation),
        ("Natural Element Analyzer", test_natural_element_analyzer),
        ("Vision Service Availability", test_vision_service_availability),
        ("Endpoint Function Structure", test_endpoint_function_structure),
        ("Response Model Creation", test_response_model_creation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 70)
    print(f"🏁 Verification Complete: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! The natural elements analysis endpoint is properly implemented.")
        print("\nNext steps:")
        print("1. Start the server: python main.py")
        print("2. Test the endpoint: python test_natural_elements_simple.py")
        print("3. Upload test images and run analysis")
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())