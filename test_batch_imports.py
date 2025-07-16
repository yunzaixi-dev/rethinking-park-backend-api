#!/usr/bin/env python3
"""
Simple test to verify batch processing imports work correctly
"""

def test_imports():
    """Test all batch processing imports"""
    try:
        # Test service import
        from services.batch_processing_service import batch_processing_service, BatchProcessingService
        print("✅ BatchProcessingService imported successfully")
        
        # Test models import
        from models.image import (
            BatchProcessingRequest,
            BatchOperationRequest,
            BatchProcessingResponse,
            BatchJobStatus,
            BatchResultsResponse,
            BatchOperationResult
        )
        print("✅ Batch processing models imported successfully")
        
        # Test enum imports
        from services.batch_processing_service import BatchOperationType, BatchOperationStatus
        print("✅ Batch processing enums imported successfully")
        
        # Test service initialization
        print(f"✅ Service initialized with {len(batch_processing_service.operation_handlers)} operation handlers")
        
        # Test operation types
        operation_types = [op.value for op in BatchOperationType]
        print(f"✅ Supported operation types: {operation_types}")
        
        # Test service statistics
        stats = batch_processing_service.get_service_statistics()
        print(f"✅ Service statistics: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n🎉 All imports successful! Batch processing is properly configured.")
    else:
        print("\n❌ Import test failed. Please check the implementation.")
    
    exit(0 if success else 1)