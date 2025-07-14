import os
from typing import List

class Settings:
    # 应用基本配置
    APP_NAME: str = "Rethinking Park Backend API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # Google Cloud配置
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_CLOUD_STORAGE_BUCKET: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    
    # 文件上传限制
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    # Redis缓存配置
    REDIS_ENABLED: bool = True
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_HOURS: int = 24
    
    # 速率限制配置
    RATE_LIMIT_ENABLED: bool = True
    
    # 图像哈希配置
    ENABLE_DUPLICATE_DETECTION: bool = True
    SIMILARITY_THRESHOLD: int = 5  # 汉明距离阈值
    
    def __init__(self):
        # 简单的环境变量读取，避免pydantic复杂性
        self.APP_NAME = os.getenv("APP_NAME", self.APP_NAME)
        self.APP_VERSION = os.getenv("APP_VERSION", self.APP_VERSION)
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.API_V1_STR = os.getenv("API_V1_STR", self.API_V1_STR)
        
        # Google Cloud配置
        self.GOOGLE_CLOUD_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "")
        self.GOOGLE_CLOUD_STORAGE_BUCKET = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET", "")
        self.GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        
        # Redis配置
        self.REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
        self.REDIS_URL = os.getenv("REDIS_URL", self.REDIS_URL)
        self.CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))
        
        # 功能配置
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.ENABLE_DUPLICATE_DETECTION = os.getenv("ENABLE_DUPLICATE_DETECTION", "true").lower() == "true"
        self.SIMILARITY_THRESHOLD = int(os.getenv("SIMILARITY_THRESHOLD", "5"))
        
        # CORS配置 - 简单处理
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
        if allowed_origins == "*":
            self.ALLOWED_ORIGINS = ["*"]
        else:
            self.ALLOWED_ORIGINS = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]

# 创建配置实例
settings = Settings()
