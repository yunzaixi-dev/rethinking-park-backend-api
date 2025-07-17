# 开发指南

## 概述

本文档为 Rethinking Park Backend API 的开发者提供详细的开发指南，包括项目结构、开发环境设置、编码规范、测试策略等。

## 项目结构

```
rethinking-park-backend-api/
├── app/                          # 主应用代码
│   ├── __init__.py
│   ├── main.py                   # FastAPI应用入口
│   ├── config/                   # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py           # 应用配置
│   │   ├── base.py               # 基础配置类
│   │   ├── app.py                # 应用配置
│   │   ├── database.py           # 数据库配置
│   │   ├── cache.py              # 缓存配置
│   │   ├── external.py           # 外部服务配置
│   │   └── loader.py             # 配置加载器
│   ├── api/                      # API路由
│   │   ├── __init__.py
│   │   └── v1/                   # API版本1
│   │       ├── __init__.py
│   │       ├── endpoints/        # API端点
│   │       │   ├── __init__.py
│   │       │   ├── images.py     # 图像相关API
│   │       │   ├── analysis.py   # 分析相关API
│   │       │   ├── health.py     # 健康检查API
│   │       │   ├── admin.py      # 管理API
│   │       │   └── batch.py      # 批量操作API
│   │       └── router.py         # 路由聚合
│   ├── core/                     # 核心功能
│   │   ├── __init__.py
│   │   ├── middleware.py         # 中间件
│   │   └── exceptions.py         # 异常处理
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── base.py               # 基础模型
│   │   ├── image.py              # 图像模型
│   │   ├── analysis.py           # 分析模型
│   │   └── validators.py         # 验证器
│   ├── services/                 # 业务服务
│   │   ├── __init__.py
│   │   ├── base.py               # 基础服务类
│   │   ├── dependencies.py       # 依赖注入
│   │   ├── image/                # 图像处理服务
│   │   │   ├── __init__.py
│   │   │   └── processing.py     # 图像处理
│   │   ├── vision/               # 视觉服务
│   │   │   ├── __init__.py
│   │   │   └── google_vision.py  # Google Vision API
│   │   ├── cache/                # 缓存服务
│   │   │   ├── __init__.py
│   │   │   └── redis_cache.py    # Redis缓存
│   │   └── external/             # 外部服务
│   │       ├── __init__.py
│   │       └── gcs.py            # Google Cloud Storage
│   └── utils/                    # 工具函数
│       └── __init__.py
├── services/                     # 独立服务模块
│   ├── __init__.py
│   ├── enhanced_vision_service.py
│   ├── image_processing_service.py
│   ├── cache_service.py
│   ├── batch_processing_service.py
│   └── error_handling.py
├── models/                       # 数据模型（兼容性）
│   ├── __init__.py
│   └── image.py
├── tests/                        # 测试代码
│   ├── __init__.py
│   ├── conftest.py               # pytest配置
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   └── e2e/                      # 端到端测试
├── scripts/                      # 脚本文件
│   ├── setup/                    # 设置脚本
│   ├── deployment/               # 部署脚本
│   ├── testing/                  # 测试脚本
│   └── maintenance/              # 维护脚本
├── deployment/                   # 部署配置
│   ├── docker-compose.dev.yml
│   ├── docker-compose.staging.yml
│   ├── production.yml
│   ├── nginx.conf
│   └── prometheus.yml
├── docs/                         # 文档
│   ├── api/                      # API文档
│   ├── deployment/               # 部署文档
│   └── development/              # 开发文档
├── config/                       # 配置文件
│   ├── local.env
│   ├── staging.env
│   └── production.env
├── requirements.txt              # Python依赖
├── Dockerfile                    # Docker配置
├── docker-compose.yml            # Docker Compose配置
├── Makefile                      # 构建脚本
├── pytest.ini                   # pytest配置
└── README.md                     # 项目说明
```

## 开发环境设置

### 1. 系统要求

- Python 3.8+
- Redis 6.0+
- Docker 20.10+ (可选)
- Google Cloud SDK (可选)

### 2. 快速设置

```bash
# 克隆项目
git clone <repository-url>
cd rethinking-park-backend-api

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env

# 编辑配置文件
nano .env
```

### 3. 配置 Google Cloud

参考 [Google Cloud 配置教程](../deployment/google-cloud-setup.md) 完成 Google Cloud 服务的配置。

### 4. 启动开发服务器

```bash
# 启动 Redis (如果本地安装)
redis-server

# 启动开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Python 直接运行
python main.py
```

## 开发工作流

### 1. 分支管理

```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 开发完成后提交
git add .
git commit -m "feat: add your feature description"

# 推送分支
git push origin feature/your-feature-name

# 创建 Pull Request
```

### 2. 代码规范

#### Python 代码风格

使用 [PEP 8](https://pep8.org/) 作为基础代码风格，并使用以下工具：

```bash
# 安装开发工具
pip install black flake8 isort mypy

# 代码格式化
black .

# 导入排序
isort .

# 代码检查
flake8 .

# 类型检查
mypy .
```

#### 命名规范

- **文件名**: 使用小写字母和下划线 (`image_service.py`)
- **类名**: 使用 PascalCase (`ImageService`)
- **函数名**: 使用 snake_case (`process_image`)
- **常量**: 使用大写字母和下划线 (`MAX_FILE_SIZE`)
- **变量**: 使用 snake_case (`image_data`)

#### 文档字符串

```python
def process_image(image_data: bytes, analysis_type: str) -> dict:
    """
    处理图像并返回分析结果
    
    Args:
        image_data: 图像二进制数据
        analysis_type: 分析类型 ('labels', 'faces', 'text')
    
    Returns:
        包含分析结果的字典
    
    Raises:
        ValueError: 当分析类型不支持时
        ProcessingError: 当图像处理失败时
    """
    pass
```

### 3. 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
# 功能添加
git commit -m "feat: add image duplicate detection"

# 错误修复
git commit -m "fix: resolve Redis connection timeout"

# 文档更新
git commit -m "docs: update API documentation"

# 重构
git commit -m "refactor: improve error handling structure"

# 测试
git commit -m "test: add unit tests for image service"

# 构建/部署
git commit -m "build: update Docker configuration"
```

## 架构设计

### 1. 分层架构

```
┌─────────────────┐
│   API Layer    │  ← FastAPI 路由和端点
├─────────────────┤
│ Service Layer   │  ← 业务逻辑和服务
├─────────────────┤
│  Model Layer    │  ← 数据模型和验证
├─────────────────┤
│Infrastructure   │  ← 外部服务和存储
└─────────────────┘
```

### 2. 依赖注入

使用 FastAPI 的依赖注入系统：

```python
# services/dependencies.py
from functools import lru_cache
from app.config import settings
from services.cache_service import CacheService

@lru_cache()
def get_cache_service() -> CacheService:
    return CacheService(settings.cache)

# api/v1/endpoints/images.py
from fastapi import Depends
from services.dependencies import get_cache_service

@router.post("/analyze")
async def analyze_image(
    request: AnalyzeRequest,
    cache_service: CacheService = Depends(get_cache_service)
):
    # 使用注入的服务
    pass
```

### 3. 错误处理

统一的错误处理机制：

```python
# core/exceptions.py
class APIException(Exception):
    def __init__(self, message: str, code: str = None, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code

class ImageNotFoundError(APIException):
    def __init__(self, image_id: str):
        super().__init__(
            message=f"Image {image_id} not found",
            code="IMAGE_NOT_FOUND",
            status_code=404
        )

# main.py
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )
```

## 测试策略

### 1. 测试分层

- **单元测试**: 测试单个函数/类的功能
- **集成测试**: 测试服务间的集成
- **端到端测试**: 测试完整的用户场景

### 2. 测试工具

```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov httpx

# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_image_service.py

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 3. 测试示例

```python
# tests/unit/test_image_service.py
import pytest
from unittest.mock import Mock, patch
from services.image_processing_service import ImageProcessingService

class TestImageProcessingService:
    @pytest.fixture
    def service(self):
        return ImageProcessingService()
    
    @pytest.fixture
    def sample_image_data(self):
        # 返回测试图像数据
        pass
    
    def test_calculate_hash(self, service, sample_image_data):
        """测试图像哈希计算"""
        hash_value = service.calculate_hash(sample_image_data)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hash length
    
    @patch('services.image_processing_service.vision')
    async def test_analyze_image(self, mock_vision, service, sample_image_data):
        """测试图像分析"""
        # 模拟 Vision API 响应
        mock_vision.ImageAnnotatorClient.return_value.label_detection.return_value = Mock()
        
        result = await service.analyze_image(sample_image_data, "labels")
        assert "labels" in result
```

### 4. 测试配置

```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from main import app

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    """创建测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_image():
    """提供测试图像"""
    # 返回测试图像数据
    pass
```

## 性能优化

### 1. 缓存策略

```python
# 使用 Redis 缓存分析结果
@cache_result(ttl=86400)  # 24小时
async def analyze_image(image_hash: str, analysis_type: str):
    # 分析逻辑
    pass

# 使用内存缓存配置
@lru_cache(maxsize=1000)
def get_image_metadata(image_id: str):
    # 获取图像元数据
    pass
```

### 2. 异步处理

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 异步处理多个图像
async def process_multiple_images(image_list):
    tasks = [process_single_image(img) for img in image_list]
    results = await asyncio.gather(*tasks)
    return results

# 使用线程池处理 CPU 密集型任务
executor = ThreadPoolExecutor(max_workers=4)

async def cpu_intensive_task(data):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, heavy_computation, data)
    return result
```

### 3. 数据库优化

```python
# 使用批量操作
async def batch_insert_images(images: List[ImageModel]):
    # 批量插入而不是逐个插入
    pass

# 使用索引优化查询
# 在数据库中为常用查询字段创建索引
```

## 监控和日志

### 1. 日志配置

```python
import logging
import structlog

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# 使用示例
logger.info("Image processed", image_id=image_id, processing_time=0.5)
```

### 2. 性能监控

```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                "Function executed",
                function=func.__name__,
                duration=duration,
                status="success"
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Function failed",
                function=func.__name__,
                duration=duration,
                error=str(e),
                status="error"
            )
            raise
    return wrapper

@monitor_performance
async def analyze_image(image_data):
    # 分析逻辑
    pass
```

## 部署准备

### 1. 环境变量检查

```python
# scripts/check_env.py
import os
from typing import List

REQUIRED_VARS = [
    "GOOGLE_CLOUD_PROJECT_ID",
    "GOOGLE_CLOUD_STORAGE_BUCKET",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "REDIS_URL"
]

def check_environment() -> List[str]:
    missing = []
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)
    return missing

if __name__ == "__main__":
    missing = check_environment()
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        exit(1)
    else:
        print("All required environment variables are set")
```

### 2. 健康检查

```python
# api/v1/endpoints/health.py
@router.get("/health-detailed")
async def detailed_health_check():
    checks = {
        "google_cloud": await check_google_cloud(),
        "redis": await check_redis(),
        "storage": await check_storage()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

## 常见问题解决

### 1. 开发环境问题

**问题**: Redis 连接失败
```bash
# 检查 Redis 状态
redis-cli ping

# 启动 Redis
redis-server

# 或使用 Docker
docker run -d -p 6379:6379 redis:alpine
```

**问题**: Google Cloud 认证失败
```bash
# 检查服务账号密钥
export GOOGLE_APPLICATION_CREDENTIALS="./service-account-key.json"

# 测试连接
python -c "from google.cloud import storage; print('OK')"
```

### 2. 性能问题

**问题**: API 响应慢
- 检查缓存命中率
- 优化数据库查询
- 使用异步处理
- 添加性能监控

**问题**: 内存使用过高
- 检查缓存大小设置
- 优化图像处理流程
- 使用流式处理大文件

### 3. 测试问题

**问题**: 测试运行缓慢
- 使用模拟对象替代真实服务调用
- 并行运行测试
- 优化测试数据准备

## 最佳实践

1. **代码组织**: 保持模块职责单一，避免循环依赖
2. **错误处理**: 使用统一的错误处理机制
3. **日志记录**: 记录关键操作和错误信息
4. **测试覆盖**: 保持高测试覆盖率
5. **性能监控**: 监控关键指标和性能
6. **安全考虑**: 验证输入，保护敏感信息
7. **文档维护**: 保持代码和文档同步更新

## 参考资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Google Cloud Python SDK](https://cloud.google.com/python/docs)
- [Redis Python 客户端](https://redis-py.readthedocs.io/)
- [pytest 文档](https://docs.pytest.org/)
- [Python 代码风格指南](https://pep8.org/)