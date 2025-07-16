#!/usr/bin/env python3
"""
Test only the batch processing models without running services
"""

def test_models():
    """Test batch processing models"""
    try:
        print("Testing batch processing models...")
        
        # Test model imports
        from models.image import (
            BatchProcessingRequest,
            BatchOperationRequest,
            BatchProcessingResponse,
            BatchJobStatus,
            BatchResultsResponse,
            BatchOperationResult
        )
        print("✅ All models imported successfully")
        
        # Test model creation
        operation = BatchOperationRequest(
            type="detect_objects",
            image_hash="test_hash",
            parameters={"confidence_threshold": 0.5}
        )
        print("✅ BatchOperationRequest created")
        
        batch_request = BatchProcessingRequest(
            operations=[operation]
        )
        print("✅ BatchProcessingRequest created")
        
        print("🎉 All model tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_models()
    exit(0 if success else 1)