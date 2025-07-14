# Rethinking Park Backend API

智能公园图像分析后端API，基于FastAPI和Google Cloud服务构建。

## 功能特性

- 🖼️ **图像上传**: 支持多种图像格式的安全上传
- 🔍 **智能分析**: 使用Google Cloud Vision API进行图像内容分析
- ☁️ **云存储**: 集成Google Cloud Storage进行图像存储
- 📊 **元数据管理**: 完整的图像信息和分析结果存储
- 🚀 **高性能**: 基于FastAPI的异步处理
- 📝 **自动文档**: 内置Swagger UI和ReDoc文档

## 主要API端点

### 1. 图像上传 API
```
POST /api/v1/upload
```
- 上传图像文件
- 返回唯一的图像ID
- 自动上传到Google Cloud Storage

### 2. 图像分析 API
```
POST /api/v1/analyze
```
- 使用图像ID进行智能分析
- 支持多种分析类型（对象检测、文本识别、标签分类等）
- 返回详细的分析结果

### 其他端点
- `GET /api/v1/images` - 列出所有图像
- `GET /api/v1/image/{image_id}` - 获取特定图像信息
- `DELETE /api/v1/image/{image_id}` - 删除图像
- `GET /api/v1/stats` - 获取系统统计信息
- `GET /health` - 健康检查

## 安装和配置

### 1. 克隆项目
```bash
cd rethinkingpark-backend-v2
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置Google Cloud

#### 创建Google Cloud项目
1. 访问 [Google Cloud Console](https://console.cloud.google.com)
2. 创建新项目或选择现有项目
3. 启用以下API：
   - Cloud Storage API
   - Cloud Vision API

#### 创建服务账号
1. 在IAM & Admin > Service Accounts 中创建服务账号
2. 为服务账号分配以下角色：
   - Storage Admin
   - Cloud Vision API User
3. 创建JSON密钥文件，保存为 `service-account-key.json`

#### 创建Storage存储桶
```bash
gsutil mb gs://your-bucket-name
```

### 4. 环境配置
复制 `env.example` 为 `.env` 并修改配置：
```bash
cp env.example .env
```

编辑 `.env` 文件：
```env
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
DEBUG=True
```

## 运行应用

### 开发模式
```bash
python main.py
```
或
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker方式
```bash
# 构建镜像
docker build -t rethinking-park-api .

# 运行容器
docker run -p 8000:8000 -v $(pwd)/.env:/app/.env -v $(pwd)/service-account-key.json:/app/service-account-key.json rethinking-park-api
```

## API文档

启动服务后，访问以下地址查看API文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 使用示例

### 上传图像
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-image.jpg"
```

响应：
```json
{
  "image_id": "uuid-string",
  "filename": "your-image.jpg",
  "file_size": 1024000,
  "content_type": "image/jpeg",
  "gcs_url": "https://storage.googleapis.com/...",
  "upload_time": "2024-01-01T12:00:00Z",
  "status": "uploaded"
}
```

### 分析图像
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "image_id": "your-image-id",
    "analysis_type": "comprehensive"
  }'
```

## 支持的分析类型

- `comprehensive` - 综合分析（包含所有类型）
- `objects` - 对象检测
- `text` - 文本识别
- `landmarks` - 地标识别
- `labels` - 标签分类
- `faces` - 人脸检测
- `safety` - 安全内容检测

## 技术栈

- **FastAPI** - 现代化的Python Web框架
- **Google Cloud Storage** - 图像存储
- **Google Cloud Vision** - 图像分析
- **Pydantic** - 数据验证
- **Uvicorn** - ASGI服务器
- **Docker** - 容器化部署

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 支持

如有问题，请创建Issue或联系开发团队。 