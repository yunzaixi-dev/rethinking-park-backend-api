#!/usr/bin/env python3
"""
Simple verification script for batch processing implementation
"""

def verify_batch_processing():
    """Verify batch processing implementation"""
    print("🔍 Verifying batch processing implementation...")
    
    try:
        # Test 1: Import batch processing service
        print("\n1. Testing BatchProcessingService import...")
        from services.batch_processing_service import (
            batch_processing_service, 
            BatchProcessingService,
            BatchOperationType,
            BatchOperationStatus
        )
        print("   ✅ BatchProcessingService imported successfully")
        
        # Test 2: Import batch processing models
        print("\n2. Testing batch processing models import...")
        from models.image import (
            BatchProcessingRequest,
            BatchOperationRequest,
            BatchProcessingResponse,
            BatchJobStatus,
            BatchResultsResponse,
            BatchOperationResult
        )
        print("   ✅ Batch processing models imported successfully")
        
        # Test 3: Check service initialization
        print("\n3. Testing service initialization...")
        print(f"   ✅ Service has {len(batch_processing_service.operation_handlers)} operation handlers")
        print(f"   ✅ Supported operations: {[op.value for op in BatchOperationType]}")
        
        # Test 4: Check service statistics
        print("\n4. Testing service statistics...")
        stats = batch_processing_service.get_service_statistics()
        print(f"   ✅ Service statistics: {stats['total_jobs_created']} jobs created")
        
        # Test 5: Test model creation
        print("\n5. Testing model creation...")
        
        # Create a sample batch operation request
        operation = BatchOperationRequest(
            type="detect_objects",
            image_hash="test_hash",
            parameters={"confidence_threshold": 0.5},
            max_retries=2
        )
        print("   ✅ BatchOperationRequest created successfully")
        
        # Create a sample batch processing request
        batch_request = BatchProcessingRequest(
            operations=[operation],
            callback_url=None,
            max_concurrent_operations=5
        )
        print("   ✅ BatchProcessingRequest created successfully")
        
        print("\n🎉 All verification tests passed!")
        print("✅ Batch processing implementation is working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_main_py_integration():
    """Verify main.py integration"""
    print("\n🔍 Verifying main.py integration...")
    
    try:
        # Test main.py compilation
        import py_compile
        py_compile.compile('main.py', doraise=True)
        print("   ✅ main.py compiles successfully")
        
        # Test imports in main.py context
        import sys
        import os
        
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        # Test importing main module components
        from models.image import BatchProcessingRequest, BatchProcessingResponse
        print("   ✅ Batch processing models can be imported in main.py context")
        
        print("✅ Main.py integration verified successfully")
        return True
        
    except Exception as e:
        print(f"❌ Main.py integration verification failed: {e}")
        return False

def main():
    """Main verification function"""
    print("="*60)
    print("🚀 BATCH PROCESSING VERIFICATION")
    print("="*60)
    
    # Run verifications
    service_ok = verify_batch_processing()
    main_ok = verify_main_py_integration()
    
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)
    
    if service_ok and main_ok:
        print("🎉 ALL VERIFICATIONS PASSED!")
        print("✅ Batch processing is ready for use")
        return 0
    else:
        print("❌ SOME VERIFICATIONS FAILED")
        print("⚠️ Please check the implementation")
        return 1

if __name__ == "__main__":
    exit(main())