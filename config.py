import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用基本配置
    APP_NAME: str = "Rethinking Park Backend API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Google Cloud配置
    GOOGLE_CLOUD_PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "")
    GOOGLE_CLOUD_STORAGE_BUCKET: str = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # 文件上传限制
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    # Redis缓存配置
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))
    
    # 速率限制配置
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    
    # 图像哈希配置
    ENABLE_DUPLICATE_DETECTION: bool = os.getenv("ENABLE_DUPLICATE_DETECTION", "true").lower() == "true"
    SIMILARITY_THRESHOLD: int = int(os.getenv("SIMILARITY_THRESHOLD", "5"))  # 汉明距离阈值
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建配置实例
settings = Settings() 