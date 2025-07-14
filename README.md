# Rethinking Park Backend API v2.0

智能公园图像分析后端API - 支持图像哈希去重、智能缓存和速率限制的Google Cloud Vision图像分析服务。

## 🚀 新功能亮点 (v2.0)

### 1. 📊 图像哈希去重
- **MD5哈希**: 精确检测完全相同的图像
- **感知哈希**: 检测视觉相似的图像
- **自动去重**: 相同图像只存储一次，节省存储空间
- **相似度检测**: 可配置的相似度阈值

### 2. ⚡ 智能缓存系统
- **Redis缓存**: 缓存Vision API分析结果
- **自动缓存**: 首次分析后自动缓存24小时
- **快速响应**: 缓存命中时响应速度提升10倍+
- **成本优化**: 避免重复调用昂贵的Vision API

### 3. 🛡️ API速率限制
- **分级限制**: 不同API端点有不同的速率限制
- **IP限制**: 基于客户端IP的访问频率控制
- **优雅降级**: 超出限制时返回友好错误信息
- **可配置**: 支持环境变量配置限制策略

### 4. 🔍 基于哈希的API
- **哈希标识**: 使用图像哈希作为唯一标识符
- **向后兼容**: 保持对原有ID-based API的支持
- **重复检测API**: 专门的重复检测端点
- **批量操作**: 支持基于哈希的批量处理

## 📋 API端点

### 图像上传
```http
POST /api/v1/upload
```
- 上传图像并返回哈希值
- 自动检测重复和相似图像
- 速率限制: 10次/分钟

### 图像分析 (基于哈希)
```http
POST /api/v1/analyze
{
    "image_hash": "abc123def456...",
    "analysis_type": "labels",
    "force_refresh": false
}
```
- 使用图像哈希进行分析
- 自动缓存分析结果
- 速率限制: 5次/分钟

### 图像分析 (基于ID - 向后兼容)
```http
POST /api/v1/analyze-by-id
{
    "image_id": "uuid-string",
    "analysis_type": "labels"
}
```

### 重复检测
```http
GET /api/v1/check-duplicate/{image_hash}
```
- 检查图像是否重复
- 返回相似图像列表

### 系统统计
```http
GET /api/v1/stats
```
- 存储统计信息
- 缓存性能统计
- 系统配置状态

## 🛠️ 环境配置

### 基础配置
```env
# Google Cloud 配置
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# 应用配置
DEBUG=false
APP_NAME="Rethinking Park Backend API"
APP_VERSION="2.0.0"
```

### Redis缓存配置
```env
# Redis缓存配置
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379
CACHE_TTL_HOURS=24
```

### 速率限制配置
```env
# 速率限制配置
RATE_LIMIT_ENABLED=true
```

### 重复检测配置
```env
# 图像重复检测配置
ENABLE_DUPLICATE_DETECTION=true
SIMILARITY_THRESHOLD=5  # 汉明距离阈值
```

## 🚀 快速开始

### 1. 安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Redis (Arch Linux)
sudo pacman -S redis
# 或使用yay
yay -S redis

# 启动Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 2. 配置环境
```bash
# 复制配置文件
cp env.example .env

# 编辑配置文件
nano .env
```

### 3. 启动服务
```bash
# 开发模式
python main.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 测试功能
```bash
# 运行增强功能测试
python test_enhanced_features.py

# 运行Google Cloud测试
python test_gcp.py
```

## 📊 API速率限制

| 端点类型 | 限制 | 说明 |
|---------|------|------|
| 上传 | 10次/分钟 | 图像上传API |
| 分析 | 5次/分钟 | Vision API分析（昂贵） |
| 查询 | 30次/分钟 | 列表、获取信息等 |
| 删除 | 5次/分钟 | 删除操作 |
| 默认 | 20次/分钟, 100次/小时 | 其他API |

## 🎯 性能优化

### 缓存策略
- **分析结果缓存**: 24小时TTL
- **重复图像检测**: 避免重复存储
- **哈希索引**: 快速查找和匹配

### 存储优化
- **基于哈希的文件名**: 避免重复存储
- **元数据分离**: 快速查询不下载文件
- **批量操作**: 支持批量处理

## 🔧 故障排除

### Redis连接问题
```bash
# 检查Redis状态
sudo systemctl status redis

# 测试Redis连接
redis-cli ping
```

### 速率限制调试
- 检查 `RATE_LIMIT_ENABLED` 环境变量
- 查看API响应头中的限制信息
- 调整各端点的限制配置

### 缓存问题
```bash
# 查看缓存键
redis-cli keys "analysis:*"

# 清除所有缓存
redis-cli flushall
```

## 📝 API文档

启动服务后访问:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 测试

### 单元测试
```bash
# Google Cloud配置测试
python test_gcp.py

# 增强功能测试
python test_enhanced_features.py
```

### 手动测试
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
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## �� 许可证

MIT License 