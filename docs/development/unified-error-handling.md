# 统一错误处理系统集成文档

## 概述

本文档描述了统一错误处理系统在整个应用中的集成情况，包括异常类层次结构、错误监控机制和错误恢复策略。

## 异常类层次结构

### 基础异常类

```python
APIException
├── ClientError (4xx)
│   ├── ValidationError (400)
│   ├── AuthenticationError (401)
│   ├── AuthorizationError (403)
│   ├── NotFoundError (404)
│   │   └── ImageNotFoundError (404)
│   ├── ConflictError (409)
│   └── RateLimitError (429)
└── ServerError (5xx)
    ├── ProcessingError (500)
    │   └── ImageProcessingError (500)
    ├── ServiceError (500)
    │   ├── CacheError (500)
    │   └── DatabaseError (500)
    ├── ServiceUnavailableError (503)
    ├── ExternalServiceError (502)
    │   ├── VisionServiceError (502)
    │   └── StorageError (502)
    └── TimeoutError (504)
```

## 集成的模块

### 1. 核心异常处理模块

**文件**: `app/core/exceptions.py`
- 定义了完整的异常类层次结构
- 实现了统一的异常处理器
- 提供标准化的错误响应格式

**文件**: `app/core/error_monitoring.py`
- 错误监控和日志记录
- 错误恢复机制（重试、断路器）
- 错误统计和分析

### 2. 服务层集成

#### 图像处理服务
**文件**: `services/image_processing_service.py`
- 使用 `@error_handler` 装饰器
- 抛出 `ImageProcessingError` 和 `ValidationError`
- 集成错误日志记录

```python
@error_handler("extract_by_bounding_box", reraise=True)
def extract_by_bounding_box(self, ...):
    try:
        # 处理逻辑
    except ValidationError:
        raise
    except Exception as e:
        log_error(logger, e, {"operation": "extract_by_bounding_box"})
        raise ImageProcessingError(f"Extraction failed: {str(e)}")
```

#### 增强视觉服务
**文件**: `services/enhanced_vision_service.py`
- 使用统一的 `VisionServiceError` 和 `ProcessingError`
- 集成错误监控和日志记录
- 替换了原有的自定义错误处理

#### 缓存服务
**文件**: `services/cache_service.py`
- 使用 `CacheError` 和 `ServiceUnavailableError`
- 集成错误监控
- 优雅降级处理

#### GCS存储服务
**文件**: `services/gcs_service.py`
- 使用 `StorageError` 和 `ServiceUnavailableError`
- 统一的外部服务错误处理
- 集成错误日志记录

### 3. API端点集成

#### 图像API端点
**文件**: `app/api/v1/endpoints/images.py`
- 使用 `@error_handler` 装饰器
- 抛出具体的业务异常而不是通用的 `HTTPException`
- 统一的错误响应格式

```python
@router.post("/upload", response_model=ImageUploadResponse)
@error_handler("upload_image", reraise=True)
async def upload_image(request: Request, file: UploadFile = File(...)):
    try:
        # 处理逻辑
        if not is_valid:
            raise ValidationError(validation_message)
    except (ValidationError, StorageError, ProcessingError):
        raise
    except Exception as e:
        log_error(logger, e, {"operation": "upload_image"})
        raise ProcessingError(f"Image upload failed: {str(e)}")
```

#### 分析API端点
**文件**: `app/api/v1/endpoints/analysis.py`
- 集成统一错误处理装饰器
- 使用业务特定的异常类型
- 标准化错误响应

### 4. 应用入口集成

**文件**: `app/main.py`
- 初始化错误监控系统
- 设置统一的异常处理器
- 添加错误统计端点

```python
# 设置异常处理器
setup_exception_handlers(app)

# 初始化错误监控
setup_logging(log_level="INFO", log_file="logs/app.log")

# 错误统计端点
@app.get("/errors/stats")
async def error_statistics():
    return get_error_stats()
```

## 错误处理特性

### 1. 统一错误响应格式

所有API错误都返回统一的JSON格式：

```json
{
  "error": {
    "id": "uuid-error-id",
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "timestamp": "2024-01-01T12:00:00Z",
    "path": "/api/v1/endpoint",
    "details": {
      "field": "specific_field",
      "operation": "specific_operation"
    }
  }
}
```

### 2. 错误监控和统计

- 自动记录所有错误到监控系统
- 提供错误统计和分析
- 支持错误历史记录和趋势分析

### 3. 错误恢复机制

#### 重试机制
```python
@ErrorRecovery.retry_with_backoff(max_retries=3, backoff_factor=1.0)
async def unreliable_operation():
    # 可能失败的操作
```

#### 断路器模式
```python
@ErrorRecovery.circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def external_service_call():
    # 外部服务调用
```

### 4. 结构化日志记录

- 统一的日志格式
- 包含错误上下文信息
- 支持日志聚合和分析

```python
log_error(logger, exception, {
    "operation": "image_processing",
    "image_hash": "abc123",
    "user_id": "user123"
}, "Additional context message")
```

## 使用指南

### 1. 在服务中使用统一错误处理

```python
from app.core.exceptions import ProcessingError, ValidationError
from app.core.error_monitoring import error_handler, log_error

@error_handler("service_operation", reraise=True)
async def service_method(self, data):
    try:
        # 验证输入
        if not self.validate(data):
            raise ValidationError("Invalid input data")
        
        # 处理逻辑
        result = await self.process(data)
        return result
        
    except ValidationError:
        # 重新抛出验证错误
        raise
    except Exception as e:
        # 记录错误并抛出处理错误
        log_error(logger, e, {"operation": "service_method"})
        raise ProcessingError(f"Operation failed: {str(e)}")
```

### 2. 在API端点中使用统一错误处理

```python
from app.core.exceptions import ImageNotFoundError, ProcessingError
from app.core.error_monitoring import error_handler

@router.get("/endpoint/{id}")
@error_handler("api_endpoint", reraise=True)
async def api_endpoint(id: str):
    # 业务逻辑
    if not resource_exists(id):
        raise ImageNotFoundError(image_id=id)
    
    return process_resource(id)
```

### 3. 错误监控和统计

```python
from app.core.error_monitoring import get_error_stats, clear_error_stats

# 获取错误统计
stats = get_error_stats()
print(f"Total errors: {stats['total_errors']}")
print(f"Error types: {stats['error_types']}")

# 清除统计（通常用于测试）
clear_error_stats()
```

## 测试

### 单元测试
- `tests/unit/test_core/test_exceptions.py` - 异常类测试
- `tests/unit/test_core/test_error_monitoring.py` - 错误监控测试

### 集成测试
- `tests/integration/test_services/test_unified_error_handling.py` - 统一错误处理集成测试

## 性能考虑

1. **错误监控开销**: 错误监控系统设计为低开销，不会显著影响应用性能
2. **内存使用**: 错误历史记录有大小限制，防止内存泄漏
3. **日志性能**: 使用异步日志记录，避免阻塞主线程

## 最佳实践

1. **使用具体的异常类型**: 避免使用通用的 `Exception`，使用业务特定的异常类型
2. **提供有用的错误信息**: 错误消息应该对用户和开发者都有帮助
3. **记录错误上下文**: 在记录错误时包含相关的上下文信息
4. **优雅降级**: 在可能的情况下，提供备用方案而不是直接失败
5. **监控错误趋势**: 定期检查错误统计，识别系统问题

## 未来改进

1. **错误分类**: 根据错误类型和频率进行自动分类
2. **告警系统**: 基于错误阈值的自动告警
3. **错误分析**: 更深入的错误模式分析和建议
4. **性能优化**: 进一步优化错误处理的性能开销