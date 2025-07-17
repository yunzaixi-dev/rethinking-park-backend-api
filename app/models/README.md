# Enhanced Models Documentation

This document describes the enhanced model system implemented for the backend API, including validation, serialization, and documentation features.

## Overview

The enhanced model system provides:

- **Comprehensive Validation**: Field-level and model-level validation with custom validators
- **Multiple Serialization Formats**: JSON, Dictionary, and XML serialization
- **Schema Generation**: Automatic JSON schema generation for API documentation
- **Business Rule Validation**: Domain-specific validation logic
- **Enhanced Documentation**: Detailed field descriptions and examples
- **Model Comparison**: Change detection and model comparison utilities

## Model Hierarchy

```
BaseModel (Enhanced Pydantic BaseModel)
├── BaseRequest (API request models)
├── BaseResponse (API response models)
├── PaginatedRequest (Paginated request models)
├── PaginatedResponse (Paginated response models)
├── ErrorResponse (Error response models)
├── ValidationErrorResponse (Validation error responses)
└── DomainModel (Domain-specific models)
    ├── ImageModel (Image-related domain models)
    │   ├── ImageInfo
    │   └── ImageUploadRequest/Response
    └── AnalysisModel (Analysis-related domain models)
        ├── EnhancedDetectionResult
        ├── FaceDetectionResult
        ├── NaturalElementsResult
        └── Various Analysis Request/Response models
```

## Key Features

### 1. Enhanced Validation

#### Field-Level Validation
```python
from app.models import ImageInfo

# This will validate the image hash format
image_info = ImageInfo(
    image_hash="a1b2c3d4e5f6789012345678901234ab",  # Must be valid MD5
    filename="test.jpg",  # Validated for invalid characters
    content_type="image/jpeg",  # Must be valid image MIME type
    gcs_url="https://storage.googleapis.com/bucket/file.jpg",  # Valid GCS URL
    file_size=1024  # Must be positive integer
)
```

#### Model-Level Validation
```python
# Business rule validation
assert image_info.validate_business_rules()

# Consistency validation (e.g., processed images must have results)
image_info.processed = True
# This would raise ValidationError if analysis_results is None
```

### 2. Multiple Serialization Formats

```python
from app.models import ImageSize
from app.models.base import SerializationFormat

size = ImageSize(width=1920, height=1080)

# Dictionary serialization
dict_data = size.serialize(SerializationFormat.DICT)
# {'width': 1920, 'height': 1080}

# JSON serialization
json_data = size.serialize(SerializationFormat.JSON)
# '{"width":1920,"height":1080}'

# XML serialization
xml_data = size.serialize(SerializationFormat.XML)
# <ImageSize><width>1920</width><height>1080</height></ImageSize>

# Enhanced options
formatted_json = size.to_json(indent=2, exclude_none=True)
```

### 3. Schema Generation

```python
from app.models import ImageInfo

# Get JSON schema for API documentation
schema = ImageInfo.get_schema()

# Get detailed field information
field_info = ImageInfo.get_field_info()
for field_name, info in field_info.items():
    print(f"{field_name}: {info['type']} (required: {info['required']})")
```

### 4. Model Comparison and Change Detection

```python
from app.models import ImageSize

size1 = ImageSize(width=1920, height=1080)
size2 = ImageSize(width=1280, height=720)

# Detect changes
changes = size1.get_changed_fields(size2)
# {'width': (1280, 1920), 'height': (720, 1080)}

# Create modified copy
modified = size1.copy_with_changes(width=2560)
```

## Model Categories

### Base Models

#### BaseModel
Enhanced Pydantic BaseModel with:
- Advanced serialization options
- Schema generation
- Model comparison utilities
- Validation helpers

#### BaseRequest/BaseResponse
Standard request/response models with:
- Request ID tracking
- Success/error status
- Timestamp information
- Validation methods

#### DomainModel
Abstract base for domain-specific models with:
- Unique ID generation
- Timestamp tracking (created_at, updated_at)
- Business rule validation
- Display name generation

### Image Models

#### ImageModel
Base class for image-related models:
- Image hash validation (MD5 format)
- Filename validation
- Business rule enforcement

#### ImageInfo
Comprehensive image information model:
- File metadata (size, type, URL)
- Processing status tracking
- Analysis results storage
- Validation for image dimensions and formats

#### Geometric Models
- **Point**: 2D coordinate with distance calculations
- **BoundingBox**: Normalized bounding box with area/intersection methods
- **ImageSize**: Image dimensions with aspect ratio calculations

### Analysis Models

#### AnalysisModel
Base class for analysis-related models:
- Analysis type enumeration
- Status tracking
- Result validation

#### Detection Results
- **DetectionResult**: Base detection with confidence validation
- **EnhancedDetectionResult**: Object detection with size classification
- **FaceDetectionResult**: Face detection with landmarks and emotions

#### Specialized Analysis
- **NaturalElementsResult**: Environmental analysis results
- **ColorInfo**: Color analysis with RGB/hex conversion
- **VegetationHealthMetrics**: Plant health assessment

## Validation System

### Custom Validators

The system includes comprehensive validators in `app/models/validators.py`:

- **validate_image_hash**: MD5 hash format validation
- **validate_filename**: Filename safety and length checks
- **validate_content_type**: Image MIME type validation
- **validate_gcs_url**: Google Cloud Storage URL format
- **validate_hex_color**: Hexadecimal color code validation
- **validate_confidence_score**: 0.0-1.0 range validation
- **validate_percentage**: 0.0-100.0 range validation
- **validate_normalized_coordinate**: 0.0-1.0 coordinate validation

### ModelValidator Utility

Complex validation logic for:
- Bounding box coordinate consistency
- RGB color component validation
- Image dimension validation
- Analysis result structure validation

## Usage Examples

### Creating and Validating Models

```python
from app.models import ImageInfo, ImageSize
from pydantic import ValidationError

try:
    # Create with validation
    image = ImageInfo(
        image_hash="a1b2c3d4e5f6789012345678901234ab",
        filename="landscape.jpg",
        file_size=2048000,
        content_type="image/jpeg",
        gcs_url="https://storage.googleapis.com/my-bucket/landscape.jpg",
        image_size=ImageSize(width=1920, height=1080)
    )
    
    # Validate business rules
    if image.validate_business_rules():
        print("Image passes all business rules")
    
    # Check processing status
    status = image.get_processing_status()
    print(f"Processing status: {status}")
    
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Working with Analysis Results

```python
from app.models.analysis import EnhancedDetectionResult, AnalysisType
from app.models import Point, BoundingBox

# Create detection result
detection = EnhancedDetectionResult(
    object_id="tree_001",
    class_name="tree",
    confidence=0.92,
    center_point=Point(x=0.6, y=0.4),
    area_percentage=18.5,
    bounding_box=BoundingBox(x=0.4, y=0.2, width=0.4, height=0.4)
)

# Check confidence level
if detection.is_high_confidence():
    print(f"High confidence detection: {detection.class_name}")

# Get relative size
size_category = detection.get_relative_size()
print(f"Object size: {size_category}")
```

### Serialization and Schema

```python
from app.models import ImageInfo

# Create model instance
image = ImageInfo(...)

# Export to different formats
json_export = image.to_json(indent=2, exclude_none=True)
dict_export = image.to_dict(exclude_unset=True)
xml_export = image.to_xml()

# Generate documentation
schema = ImageInfo.get_schema()
field_docs = ImageInfo.get_field_info()
```

## Error Handling

The enhanced models provide detailed error information:

```python
from app.models import ImageInfo
from pydantic import ValidationError

try:
    invalid_image = ImageInfo(
        image_hash="invalid",  # Invalid MD5 format
        filename="",  # Empty filename
        file_size=-1,  # Negative size
        content_type="text/plain",  # Invalid content type
        gcs_url="invalid-url"  # Invalid URL format
    )
except ValidationError as e:
    for error in e.errors():
        print(f"Field: {error['loc']}")
        print(f"Error: {error['msg']}")
        print(f"Input: {error['input']}")
```

## Best Practices

1. **Always use field validators** for data integrity
2. **Implement business rule validation** in domain models
3. **Use appropriate serialization formats** for different use cases
4. **Generate schemas** for API documentation
5. **Validate models** before processing
6. **Use model comparison** for change tracking
7. **Handle validation errors** gracefully

## Migration from Old Models

The enhanced models are backward compatible with the existing API. To migrate:

1. Import from `app.models` instead of `models`
2. Use enhanced validation features where needed
3. Update serialization calls to use new methods
4. Add business rule validation to domain logic
5. Generate schemas for API documentation

## Testing

Comprehensive tests are available in:
- `test_model_structure.py`: Basic model structure tests
- `test_enhanced_models.py`: Enhanced feature tests

Run tests with:
```bash
python test_enhanced_models.py
```

This will validate all enhanced features including validation, serialization, schema generation, and business rules.