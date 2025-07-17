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

## 🚀 快速开始

### 1. 快速安装
```bash
# 克隆项目
git clone <repository-url>
cd rethinking-park-backend-api

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp .env.example .env
# 编辑 .env 文件设置你的配置

# 启动服务
python main.py
```

### 2. Docker 快速启动
```bash
# 使用 Docker Compose
docker-compose up --build

# 或使用部署脚本
./scripts/deployment/deploy_dev.sh
```

### 3. 验证安装
```bash
# 健康检查
curl http://localhost:8000/health

# 查看 API 文档
# 浏览器访问: http://localhost:8000/docs
```

## 📚 文档

### 📖 用户文档
- **[快速开始指南](docs/development/quick-start.md)** - 5分钟快速上手
- **[Google Cloud 配置](docs/deployment/google-cloud-setup.md)** - 详细的GCP配置教程
- **[API 文档](docs/api/README.md)** - 完整的API参考文档

### 🛠️ 开发文档
- **[开发指南](docs/development/README.md)** - 开发环境设置和编码规范
- **[配置管理](docs/development/configuration.md)** - 配置系统详细说明

### 🚀 部署文档
- **[部署指南](docs/deployment/README.md)** - 多环境部署说明
- **[故障排除](docs/deployment/troubleshooting.md)** - 常见问题解决方案

## 📋 主要API端点

### 图像上传
```http
POST /api/v1/upload
```
上传图像并返回哈希值，自动检测重复和相似图像

### 图像分析
```http
POST /api/v1/analyze
{
    "image_hash": "abc123def456...",
    "analysis_type": "labels",
    "force_refresh": false
}
```
使用图像哈希进行分析，自动缓存分析结果

### 重复检测
```http
GET /api/v1/check-duplicate/{image_hash}
```
检查图像是否重复，返回相似图像列表

### 系统统计
```http
GET /api/v1/stats
```
获取存储统计、缓存性能和系统配置状态

> 📖 **完整API文档**: 查看 [API文档](docs/api/README.md) 或访问 http://localhost:8000/docs

## 🛠️ 项目结构

```
rethinking-park-backend-api/
├── app/                    # 主应用代码
│   ├── api/               # API路由
│   ├── config/            # 配置管理
│   ├── core/              # 核心功能
│   ├── models/            # 数据模型
│   ├── services/          # 业务服务
│   └── utils/             # 工具函数
├── services/              # 独立服务模块
├── tests/                 # 测试代码
├── scripts/               # 脚本文件
├── deployment/            # 部署配置
├── docs/                  # 项目文档
│   ├── api/              # API文档
│   ├── deployment/       # 部署文档
│   └── development/      # 开发文档
└── config/               # 环境配置文件
```

## ⚡ 性能特性

### 缓存策略
- **分析结果缓存**: 24小时TTL，避免重复调用Vision API
- **重复图像检测**: 基于MD5和感知哈希的智能去重
- **哈希索引**: 快速查找和匹配相似图像

### 速率限制
| 端点类型 | 限制 | 说明 |
|---------|------|------|
| 上传 | 10次/分钟 | 图像上传API |
| 分析 | 5次/分钟 | Vision API分析 |
| 查询 | 30次/分钟 | 列表、获取信息等 |
| 删除 | 5次/分钟 | 删除操作 |

## 🔧 配置

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

# Redis缓存配置
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379
CACHE_TTL_HOURS=24

# 速率限制配置
RATE_LIMIT_ENABLED=true

# 重复检测配置
ENABLE_DUPLICATE_DETECTION=true
SIMILARITY_THRESHOLD=5
```

> 📖 **详细配置说明**: 查看 [配置管理文档](docs/development/configuration.md)

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_image_service.py

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 手动测试
```bash
# 测试Google Cloud连接
python test_gcp.py

# 测试增强功能
python test_enhanced_features.py

# API测试
curl -X POST "http://localhost:8000/api/v1/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@test_image.jpg"
```

## 🚀 部署

### 开发环境
```bash
# 使用Docker Compose
docker-compose up --build

# 或使用部署脚本
./scripts/deployment/deploy_dev.sh
```

### 生产环境
```bash
# 生产部署
./scripts/deployment/deploy_production.sh

# 或使用Docker
docker-compose -f deployment/production.yml up -d
```

> 📖 **详细部署说明**: 查看 [部署指南](docs/deployment/README.md)

## 🔧 故障排除

### 常见问题
- **Redis连接问题**: 检查Redis服务状态和连接配置
- **Google Cloud认证**: 确保服务账号密钥文件路径正确
- **速率限制**: 查看API响应头中的限制信息
- **缓存问题**: 使用Redis CLI检查缓存状态

> 📖 **详细故障排除**: 查看 [故障排除指南](docs/deployment/troubleshooting.md)

## 🤝 贡献

我们欢迎各种形式的贡献！

1. **报告问题**: 在GitHub Issues中报告bug或提出功能请求
2. **提交代码**: Fork项目，创建功能分支，提交Pull Request
3. **改进文档**: 帮助改进项目文档和示例

> 📖 **开发指南**: 查看 [开发文档](docs/development/README.md) 了解开发规范

## 📄 许可证

MIT License - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 获取帮助

- **文档**: 查看 [docs/](docs/) 目录下的详细文档
- **API文档**: http://localhost:8000/docs (启动服务后访问)
- **GitHub Issues**: 报告问题或提出功能请求
- **社区支持**: Stack Overflow, Reddit等

---

🎉 **开始使用**: 查看 [快速开始指南](docs/development/quick-start.md) 立即开始！