# API 文档

## 概述

Rethinking Park Backend API 是一个基于 FastAPI 的图像分析服务，提供图像上传、分析、存储和管理功能。API 使用 Google Cloud Vision API 进行图像分析，支持多种分析类型包括标签检测、人脸检测、自然元素分析等。

## 基础信息

- **基础URL**: `http://localhost:8000` (开发环境)
- **API版本**: v1
- **API前缀**: `/api/v1`
- **文档地址**: 
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`

## 认证

当前版本的API不需要认证，但在生产环境中建议添加适当的认证机制。

## 速率限制

API实施了基于IP的速率限制：

| 端点类型 | 限制 | 说明 |
|---------|------|------|
| 上传 | 10次/分钟 | 图像上传API |
| 分析 | 5次/分钟 | Vision API分析（昂贵） |
| 查询 | 30次/分钟 | 列表、获取信息等 |
| 删除 | 5次/分钟 | 删除操作 |
| 默认 | 20次/分钟, 100次/小时 | 其他API |

## 响应格式

所有API响应都使用JSON格式，标准响应结构如下：

### 成功响应
```json
{
  "success": true,
  "data": {
    // 响应数据
  },
  "message": "操作成功"
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  }
}
```

## 主要端点

### 1. 健康检查

#### GET /health
基础健康检查端点

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "2.0.0"
}
```

#### GET /api/v1/health-detailed
详细健康检查，包含系统状态信息

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "2.0.0",
  "services": {
    "google_cloud": "connected",
    "redis": "connected",
    "storage": "available"
  },
  "system": {
    "memory_usage": "45%",
    "disk_usage": "23%"
  }
}
```

### 2. 图像上传

#### POST /api/v1/upload
上传图像文件并返回图像信息

**请求**:
- Content-Type: `multipart/form-data`
- 参数: `file` (图像文件)

**支持的图像格式**: JPG, JPEG, PNG, GIF, BMP, WEBP

**响应示例**:
```json
{
  "success": true,
  "data": {
    "image_id": "uuid-string",
    "image_hash": "md5-hash-string",
    "perceptual_hash": "phash-string",
    "filename": "original-filename.jpg",
    "size": 1024000,
    "format": "JPEG",
    "dimensions": {
      "width": 1920,
      "height": 1080
    },
    "upload_time": "2024-01-01T12:00:00Z",
    "gcs_url": "gs://bucket/path/to/image.jpg",
    "is_duplicate": false,
    "similar_images": []
  }
}
```

### 3. 图像分析

#### POST /api/v1/analyze
基于图像哈希进行分析

**请求体**:
```json
{
  "image_hash": "md5-hash-string",
  "analysis_type": "labels",
  "force_refresh": false
}
```

**分析类型**:
- `labels`: 标签检测
- `faces`: 人脸检测
- `natural_elements`: 自然元素分析
- `text`: 文本检测
- `objects`: 物体检测
- `landmarks`: 地标检测

**响应示例**:
```json
{
  "success": true,
  "data": {
    "image_hash": "md5-hash-string",
    "analysis_type": "labels",
    "results": {
      "labels": [
        {
          "description": "Park",
          "score": 0.95,
          "confidence": "HIGH"
        },
        {
          "description": "Tree",
          "score": 0.89,
          "confidence": "HIGH"
        }
      ]
    },
    "cached": true,
    "analysis_time": "2024-01-01T12:00:00Z"
  }
}
```

#### POST /api/v1/analyze-by-id
基于图像ID进行分析（向后兼容）

**请求体**:
```json
{
  "image_id": "uuid-string",
  "analysis_type": "labels"
}
```

### 4. 图像管理

#### GET /api/v1/images
获取图像列表

**查询参数**:
- `page`: 页码 (默认: 1)
- `limit`: 每页数量 (默认: 20, 最大: 100)
- `format`: 图像格式过滤
- `sort`: 排序方式 (`upload_time`, `size`, `filename`)
- `order`: 排序顺序 (`asc`, `desc`)

**响应示例**:
```json
{
  "success": true,
  "data": {
    "images": [
      {
        "image_id": "uuid-string",
        "image_hash": "md5-hash-string",
        "filename": "image.jpg",
        "size": 1024000,
        "upload_time": "2024-01-01T12:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

#### GET /api/v1/images/{image_id}
获取特定图像信息

**响应示例**:
```json
{
  "success": true,
  "data": {
    "image_id": "uuid-string",
    "image_hash": "md5-hash-string",
    "perceptual_hash": "phash-string",
    "filename": "image.jpg",
    "size": 1024000,
    "format": "JPEG",
    "dimensions": {
      "width": 1920,
      "height": 1080
    },
    "upload_time": "2024-01-01T12:00:00Z",
    "gcs_url": "gs://bucket/path/to/image.jpg",
    "analysis_history": [
      {
        "analysis_type": "labels",
        "analysis_time": "2024-01-01T12:00:00Z",
        "cached": true
      }
    ]
  }
}
```

#### DELETE /api/v1/images/{image_id}
删除图像

**响应示例**:
```json
{
  "success": true,
  "message": "图像删除成功"
}
```

### 5. 重复检测

#### GET /api/v1/check-duplicate/{image_hash}
检查图像是否重复

**响应示例**:
```json
{
  "success": true,
  "data": {
    "is_duplicate": true,
    "exact_matches": [
      {
        "image_id": "uuid-string",
        "image_hash": "same-md5-hash",
        "filename": "duplicate.jpg",
        "upload_time": "2024-01-01T11:00:00Z"
      }
    ],
    "similar_images": [
      {
        "image_id": "uuid-string",
        "image_hash": "different-md5-hash",
        "perceptual_hash": "similar-phash",
        "similarity_score": 0.95,
        "hamming_distance": 2,
        "filename": "similar.jpg",
        "upload_time": "2024-01-01T10:00:00Z"
      }
    ]
  }
}
```

### 6. 批量操作

#### POST /api/v1/batch/analyze
批量分析图像

**请求体**:
```json
{
  "image_hashes": ["hash1", "hash2", "hash3"],
  "analysis_type": "labels",
  "force_refresh": false
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "image_hash": "hash1",
        "analysis_type": "labels",
        "results": { /* 分析结果 */ },
        "status": "success"
      },
      {
        "image_hash": "hash2",
        "analysis_type": "labels",
        "error": "Image not found",
        "status": "error"
      }
    ],
    "summary": {
      "total": 3,
      "success": 2,
      "failed": 1
    }
  }
}
```

#### DELETE /api/v1/batch/delete
批量删除图像

**请求体**:
```json
{
  "image_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### 7. 系统统计

#### GET /api/v1/stats
获取系统统计信息

**响应示例**:
```json
{
  "success": true,
  "data": {
    "storage": {
      "total_images": 1000,
      "total_size": 1073741824,
      "unique_images": 950,
      "duplicate_images": 50,
      "formats": {
        "JPEG": 800,
        "PNG": 150,
        "GIF": 50
      }
    },
    "cache": {
      "hit_rate": 0.85,
      "total_requests": 10000,
      "cache_hits": 8500,
      "cache_misses": 1500
    },
    "analysis": {
      "total_analyses": 5000,
      "by_type": {
        "labels": 3000,
        "faces": 1000,
        "natural_elements": 1000
      }
    },
    "system": {
      "uptime": "7 days, 12:34:56",
      "version": "2.0.0",
      "environment": "production"
    }
  }
}
```

### 8. 缓存管理

#### DELETE /api/v1/cache/clear
清除所有缓存

**响应示例**:
```json
{
  "success": true,
  "message": "缓存清除成功"
}
```

#### DELETE /api/v1/cache/{image_hash}
清除特定图像的缓存

**响应示例**:
```json
{
  "success": true,
  "message": "图像缓存清除成功"
}
```

## 错误代码

| 错误代码 | HTTP状态码 | 说明 |
|---------|-----------|------|
| `INVALID_FILE_FORMAT` | 400 | 不支持的文件格式 |
| `FILE_TOO_LARGE` | 400 | 文件大小超出限制 |
| `IMAGE_NOT_FOUND` | 404 | 图像不存在 |
| `ANALYSIS_FAILED` | 500 | 分析失败 |
| `STORAGE_ERROR` | 500 | 存储错误 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超出速率限制 |
| `GOOGLE_CLOUD_ERROR` | 502 | Google Cloud服务错误 |

## 使用示例

### Python 示例

```python
import requests
import json

# 基础URL
BASE_URL = "http://localhost:8000/api/v1"

# 上传图像
def upload_image(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    return response.json()

# 分析图像
def analyze_image(image_hash, analysis_type="labels"):
    data = {
        "image_hash": image_hash,
        "analysis_type": analysis_type
    }
    response = requests.post(f"{BASE_URL}/analyze", json=data)
    return response.json()

# 使用示例
result = upload_image("test_image.jpg")
if result["success"]:
    image_hash = result["data"]["image_hash"]
    analysis = analyze_image(image_hash, "labels")
    print(json.dumps(analysis, indent=2))
```

### JavaScript 示例

```javascript
// 上传图像
async function uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/v1/upload', {
        method: 'POST',
        body: formData
    });
    
    return await response.json();
}

// 分析图像
async function analyzeImage(imageHash, analysisType = 'labels') {
    const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            image_hash: imageHash,
            analysis_type: analysisType
        })
    });
    
    return await response.json();
}

// 使用示例
document.getElementById('fileInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        const uploadResult = await uploadImage(file);
        if (uploadResult.success) {
            const analysisResult = await analyzeImage(
                uploadResult.data.image_hash, 
                'labels'
            );
            console.log(analysisResult);
        }
    }
});
```

### cURL 示例

```bash
# 上传图像
curl -X POST "http://localhost:8000/api/v1/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@test_image.jpg"

# 分析图像
curl -X POST "http://localhost:8000/api/v1/analyze" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "image_hash": "your-image-hash",
       "analysis_type": "labels"
     }'

# 获取图像列表
curl -X GET "http://localhost:8000/api/v1/images?page=1&limit=10" \
     -H "accept: application/json"

# 检查重复
curl -X GET "http://localhost:8000/api/v1/check-duplicate/your-image-hash" \
     -H "accept: application/json"
```

## 最佳实践

1. **缓存利用**: 相同图像的分析结果会被缓存24小时，避免重复调用
2. **批量操作**: 对于多个图像，使用批量API可以提高效率
3. **错误处理**: 始终检查响应中的 `success` 字段
4. **速率限制**: 注意API的速率限制，合理安排请求频率
5. **文件大小**: 上传前检查文件大小，避免超出限制
6. **重复检测**: 利用重复检测功能避免存储重复图像

## 更新日志

### v2.0.0
- 添加基于哈希的API
- 实现图像重复检测
- 添加智能缓存系统
- 实现速率限制
- 添加批量操作支持

### v1.0.0
- 基础图像上传和分析功能
- Google Cloud Vision API集成
- 基础的图像管理功能