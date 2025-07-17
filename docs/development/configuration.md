# 配置管理文档

## 概述

本项目采用分层配置管理系统，支持多环境配置和配置验证。配置系统分为以下几个模块：

- **应用配置** (`AppConfig`): 管理应用基本设置
- **数据库配置** (`DatabaseConfig`): 管理数据库连接和连接池设置
- **缓存配置** (`CacheConfig`): 管理Redis和内存缓存设置
- **外部服务配置** (`ExternalServicesConfig`): 管理Google Cloud等外部服务设置

## 配置文件结构

```
config/
├── local.env          # 本地开发环境配置
├── staging.env        # 测试环境配置
└── production.env     # 生产环境配置
```

## 环境配置

### 支持的环境

- `development` / `local`: 本地开发环境
- `staging`: 测试环境
- `production`: 生产环境
- `testing`: 测试环境（使用本地配置）

### 环境切换

通过设置 `ENVIRONMENT` 环境变量来切换环境：

```bash
# 开发环境
export ENVIRONMENT=development

# 测试环境
export ENVIRONMENT=staging

# 生产环境
export ENVIRONMENT=production
```

## 配置模块详解

### 1. 应用配置 (AppConfig)

管理应用的基本设置，包括：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `APP_NAME` | str | "Rethinking Park Backend API" | 应用名称 |
| `APP_VERSION` | str | "2.0.0" | 应用版本 |
| `DEBUG` | bool | False | 调试模式 |
| `ENVIRONMENT` | str | "development" | 运行环境 |
| `API_V1_STR` | str | "/api/v1" | API版本前缀 |
| `MAX_UPLOAD_SIZE` | int | 10485760 | 最大上传文件大小（字节） |
| `ALLOWED_IMAGE_EXTENSIONS` | List[str] | ['.jpg', '.jpeg', ...] | 允许的图片扩展名 |
| `RATE_LIMIT_ENABLED` | bool | True | 是否启用速率限制 |
| `RATE_LIMIT_REQUESTS` | int | 100 | 速率限制请求数 |
| `RATE_LIMIT_WINDOW` | int | 3600 | 速率限制时间窗口（秒） |

### 2. 数据库配置 (DatabaseConfig)

管理数据库连接设置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | str | None | 数据库连接URL |
| `DATABASE_HOST` | str | "localhost" | 数据库主机 |
| `DATABASE_PORT` | int | 5432 | 数据库端口 |
| `DATABASE_NAME` | str | "rethinking_park" | 数据库名称 |
| `DATABASE_USER` | str | "postgres" | 数据库用户名 |
| `DATABASE_PASSWORD` | str | "" | 数据库密码 |
| `DATABASE_POOL_SIZE` | int | 10 | 连接池大小 |
| `DATABASE_MAX_OVERFLOW` | int | 20 | 连接池最大溢出 |
| `ENABLE_READ_WRITE_SPLIT` | bool | False | 是否启用读写分离 |

### 3. 缓存配置 (CacheConfig)

管理Redis和内存缓存设置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `REDIS_ENABLED` | bool | True | 是否启用Redis |
| `REDIS_URL` | str | "redis://localhost:6379" | Redis连接URL |
| `REDIS_HOST` | str | "localhost" | Redis主机 |
| `REDIS_PORT` | int | 6379 | Redis端口 |
| `REDIS_DB` | int | 0 | Redis数据库编号 |
| `REDIS_PASSWORD` | str | None | Redis密码 |
| `CACHE_TTL_SECONDS` | int | 86400 | 缓存TTL（秒） |
| `MEMORY_CACHE_ENABLED` | bool | True | 是否启用内存缓存 |
| `MEMORY_CACHE_MAX_SIZE` | int | 1000 | 内存缓存最大条目数 |

### 4. 外部服务配置 (ExternalServicesConfig)

管理外部服务设置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `GOOGLE_CLOUD_PROJECT_ID` | str | "" | Google Cloud项目ID |
| `GOOGLE_CLOUD_STORAGE_BUCKET` | str | "" | Google Cloud存储桶名称 |
| `GOOGLE_APPLICATION_CREDENTIALS` | str | "" | Google服务账号凭证文件路径 |
| `GOOGLE_VISION_ENABLED` | bool | True | 是否启用Google Vision API |
| `MONITORING_ENABLED` | bool | True | 是否启用监控 |
| `LOG_LEVEL` | str | "INFO" | 日志级别 |
| `LOG_FORMAT` | str | "json" | 日志格式 |

## 配置使用方法

### 1. 基本使用

```python
from app.config import settings

# 访问应用配置
print(settings.app.APP_NAME)
print(settings.app.DEBUG)

# 访问数据库配置
db_url = settings.database.get_database_url()

# 访问缓存配置
redis_url = settings.cache.get_redis_url()

# 访问外部服务配置
if settings.external.is_google_cloud_configured():
    # 使用Google Cloud服务
    pass
```

### 2. 向后兼容访问

为了保持向后兼容，可以直接访问配置属性：

```python
from app.config import settings

# 这些属性会自动映射到对应的配置模块
print(settings.APP_NAME)  # 等同于 settings.app.APP_NAME
print(settings.DEBUG)     # 等同于 settings.app.DEBUG
print(settings.REDIS_URL) # 等同于 settings.cache.get_redis_url()
```

### 3. 环境特定配置

```python
from app.config import settings

# 检查当前环境
if settings.app.is_development:
    # 开发环境特定逻辑
    pass
elif settings.app.is_production:
    # 生产环境特定逻辑
    pass
```

## 配置验证

配置系统包含内置验证功能，会在应用启动时自动验证所有配置：

```python
from app.config import settings

# 手动验证所有配置
try:
    settings.validate_all()
    print("All configurations are valid")
except ConfigValidationError as e:
    print(f"Configuration error: {e}")
```

### 验证规则

- **必填字段验证**: 检查必需的配置项是否已设置
- **类型验证**: 确保配置值的类型正确
- **范围验证**: 检查数值是否在有效范围内
- **依赖验证**: 检查相关配置的依赖关系

## 配置最佳实践

### 1. 环境变量优先级

配置加载优先级（从高到低）：
1. 环境变量
2. 环境配置文件（如 `local.env`）
3. 默认值

### 2. 敏感信息处理

- 不要在配置文件中硬编码敏感信息
- 使用环境变量或密钥管理服务
- 在版本控制中排除包含敏感信息的文件

### 3. 配置文件管理

- 为每个环境创建独立的配置文件
- 使用 `.env.example` 提供配置模板
- 定期审查和更新配置文档

### 4. 配置验证

- 在应用启动时验证所有配置
- 为关键配置添加详细的验证规则
- 提供清晰的错误消息

## 故障排除

### 常见问题

1. **配置文件未找到**
   ```
   ConfigValidationError: Environment config file not found
   ```
   解决方案：确保配置文件存在于 `config/` 目录中

2. **配置验证失败**
   ```
   ConfigValidationError: GOOGLE_CLOUD_PROJECT_ID is required
   ```
   解决方案：检查必需的配置项是否已设置

3. **环境变量未生效**
   - 确保环境变量名称正确
   - 检查环境变量是否在应用启动前设置
   - 验证配置文件是否正确加载

### 调试配置

```python
from app.config import settings

# 打印所有配置
import json
print(json.dumps(settings.to_dict(), indent=2))

# 检查特定配置模块
print("App config:", settings.app.to_dict())
print("Database config:", settings.database.to_dict())
```

## 配置迁移

从旧配置系统迁移到新系统：

1. **备份现有配置**
   ```bash
   cp config.py config.py.backup
   ```

2. **创建新的环境配置文件**
   ```bash
   cp .env.example config/local.env
   # 编辑 config/local.env 设置你的配置
   ```

3. **更新代码中的配置引用**
   ```python
   # 旧方式
   from config import settings
   
   # 新方式
   from app.config import settings
   ```

4. **测试配置**
   ```bash
   python -c "from app.config import settings; print('Config loaded successfully')"
   ```