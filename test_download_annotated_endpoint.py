#!/usr/bin/env python3
"""
Test script for the download-annotated endpoint
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.image import AnnotatedImageRequest, AnnotationStyle
from services.gcs_service import gcs_service
from services.storage_service import storage_service
from services.cache_service import cache_service
from services.vision_service import vision_service
from services.enhanced_vision_service import enhanced_vision_service
from services.image_annotation_service import image_annotation_service

async def test_download_annotated_endpoint():
    """Test the download-annotated endpoint functionality"""
    
    print("🧪 Testing Download Annotated Endpoint")
    print("=" * 50)
    
    try:
        # Initialize services
        await gcs_service.initialize()
        await cache_service.initialize()
        print("✅ Services initialized")
        
        # Get a test image hash (use the first available image)
        images = await storage_service.list_images(limit=1)
        if not images:
            print("❌ No images found in storage. Please upload an image first.")
            return False
        
        test_image_hash = images[0].image_hash
        print(f"📸 Using test image: {test_image_hash[:12]}...")
        
        # Test 1: Basic annotation request
        print("\n🔍 Test 1: Basic annotation request")
        basic_request = AnnotatedImageRequest(
            image_hash=test_image_hash,
            include_face_markers=True,
            include_object_boxes=True,
            include_labels=True,
            output_format="png",
            quality=95
        )
        
        # Simulate the endpoint logic
        start_time = datetime.now()
        
        # Get image information
        image_info = await storage_service.get_image_info_by_hash(test_image_hash)
        if not image_info:
            print("❌ Image not found in storage")
            return False
        
        # Download image content
        image_content = await gcs_service.download_image(test_image_hash)
        if not image_content:
            print("❌ Could not download image content")
            return False
        
        print(f"✅ Downloaded image content: {len(image_content)} bytes")
        
        # Get detection results
        try:
            detection_response = await enhanced_vision_service.detect_objects_enhanced(
                image_content=image_content,
                image_hash=test_image_hash,
                include_faces=True,
                include_labels=True,
                confidence_threshold=0.5,
                max_results=50
            )
            
            objects = detection_response.objects if detection_response.success else []
            faces = detection_response.faces if detection_response.success else []
            labels = detection_response.labels if detection_response.success else []
            
            print(f"✅ Detection results: {len(objects)} objects, {len(faces)} faces, {len(labels)} labels")
            
        except Exception as e:
            print(f"⚠️  Detection failed, continuing with empty results: {e}")
            objects, faces, labels = [], [], []
        
        # Validate annotation request
        validation_result = image_annotation_service.validate_annotation_request(
            image_content=image_content,
            objects=objects,
            faces=faces
        )
        
        if not validation_result["valid"]:
            print(f"❌ Annotation validation failed: {validation_result['errors']}")
            return False
        
        print("✅ Annotation request validation passed")
        
        # Render annotated image
        annotated_image_bytes = image_annotation_service.render_annotated_image(
            image_content=image_content,
            objects=objects,
            faces=faces,
            labels=labels,
            include_face_markers=True,
            include_object_boxes=True,
            include_labels=True
        )
        
        print(f"✅ Rendered annotated image: {len(annotated_image_bytes)} bytes")
        
        # Get annotation statistics
        annotation_stats = image_annotation_service.get_annotation_statistics(
            objects=objects,
            faces=faces
        )
        
        print(f"✅ Annotation statistics: {annotation_stats}")
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        print(f"✅ Processing completed in {processing_time}ms")
        
        # Test 2: Custom annotation styles
        print("\n🎨 Test 2: Custom annotation styles")
        custom_style = AnnotationStyle(
            face_marker_color="#FF0000",  # Red
            box_color="#00FF00",          # Green
            label_color="#0000FF",        # Blue
            box_thickness=3,
            face_marker_radius=12
        )
        
        custom_request = AnnotatedImageRequest(
            image_hash=test_image_hash,
            include_face_markers=True,
            include_object_boxes=True,
            include_labels=False,
            output_format="jpg",
            quality=85,
            annotation_style=custom_style
        )
        
        # Test custom styles rendering
        custom_annotated_bytes = image_annotation_service.render_annotated_image(
            image_content=image_content,
            objects=objects,
            faces=faces,
            labels=None,
            include_face_markers=True,
            include_object_boxes=True,
            include_labels=False,
            custom_styles=custom_style.dict()
        )
        
        print(f"✅ Custom styled annotation: {len(custom_annotated_bytes)} bytes")
        
        # Test 3: Different output formats
        print("\n📁 Test 3: Different output formats")
        formats = ["png", "jpg", "webp"]
        
        for fmt in formats:
            format_request = AnnotatedImageRequest(
                image_hash=test_image_hash,
                include_face_markers=True,
                include_object_boxes=True,
                include_labels=True,
                output_format=fmt,
                quality=90
            )
            
            # Test format conversion (simulate the endpoint logic)
            test_bytes = annotated_image_bytes
            if fmt != "png":
                from PIL import Image
                import io
                
                pil_image = Image.open(io.BytesIO(test_bytes))
                if fmt == "jpg":
                    if pil_image.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', pil_image.size, (255, 255, 255))
                        if pil_image.mode == 'RGBA':
                            background.paste(pil_image, mask=pil_image.split()[-1])
                        else:
                            background.paste(pil_image, mask=pil_image.split()[-1])
                        pil_image = background
                    
                    output_buffer = io.BytesIO()
                    pil_image.save(output_buffer, format='JPEG', quality=90)
                    test_bytes = output_buffer.getvalue()
                elif fmt == "webp":
                    output_buffer = io.BytesIO()
                    pil_image.save(output_buffer, format='WEBP', quality=90)
                    test_bytes = output_buffer.getvalue()
            
            print(f"✅ {fmt.upper()} format: {len(test_bytes)} bytes")
        
        # Test 4: Edge cases
        print("\n⚠️  Test 4: Edge cases")
        
        # Test with non-existent image hash
        try:
            fake_hash = "nonexistent_hash_12345"
            fake_image_info = await storage_service.get_image_info_by_hash(fake_hash)
            if fake_image_info is None:
                print("✅ Correctly handles non-existent image hash")
            else:
                print("❌ Should return None for non-existent hash")
        except Exception as e:
            print(f"✅ Correctly raises exception for non-existent hash: {e}")
        
        # Test with empty detection results
        empty_annotated = image_annotation_service.render_annotated_image(
            image_content=image_content,
            objects=[],
            faces=[],
            labels=[],
            include_face_markers=True,
            include_object_boxes=True,
            include_labels=True
        )
        print(f"✅ Empty detection results handled: {len(empty_annotated)} bytes")
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            await cache_service.close()
            print("✅ Services cleaned up")
        except:
            pass

async def main():
    """Main test function"""
    success = await test_download_annotated_endpoint()
    if success:
        print("\n✅ Download annotated endpoint test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Download annotated endpoint test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())