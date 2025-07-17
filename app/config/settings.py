"""
统一配置管理

整合所有配置模块，提供统一的配置访问接口。
"""

import os

from .app import AppConfig
from .cache import CacheConfig
from .database import DatabaseConfig
from .external import ExternalServicesConfig
from .loader import config_loader


class Settings:
    """统一配置类"""

    def __init__(self):
        self.app = AppConfig()
        self.database = DatabaseConfig()
        self.cache = CacheConfig()
        self.external = ExternalServicesConfig()

    def validate_all(self) -> None:
        """验证所有配置"""
        self.app.validate_config()
        self.database.validate_config()
        self.cache.validate_config()
        self.external.validate_config()

    def to_dict(self) -> dict:
        """将所有配置转换为字典"""
        return {
            "app": self.app.to_dict(),
            "database": self.database.to_dict(),
            "cache": self.cache.to_dict(),
            "external": self.external.to_dict(),
        }

    # 向后兼容的属性访问
    @property
    def APP_NAME(self) -> str:
        return self.app.APP_NAME

    @property
    def APP_VERSION(self) -> str:
        return self.app.APP_VERSION

    @property
    def DEBUG(self) -> bool:
        return self.app.DEBUG

    @property
    def API_V1_STR(self) -> str:
        return self.app.API_V1_STR

    @property
    def GOOGLE_CLOUD_PROJECT_ID(self) -> str:
        return self.external.GOOGLE_CLOUD_PROJECT_ID

    @property
    def GOOGLE_CLOUD_STORAGE_BUCKET(self) -> str:
        return self.external.GOOGLE_CLOUD_STORAGE_BUCKET

    @property
    def GOOGLE_APPLICATION_CREDENTIALS(self) -> str:
        return self.external.GOOGLE_APPLICATION_CREDENTIALS

    @property
    def MAX_UPLOAD_SIZE(self) -> int:
        return self.app.MAX_UPLOAD_SIZE

    @property
    def ALLOWED_IMAGE_EXTENSIONS(self) -> list:
        return self.app.ALLOWED_IMAGE_EXTENSIONS

    @property
    def REDIS_ENABLED(self) -> bool:
        return self.cache.REDIS_ENABLED

    @property
    def REDIS_URL(self) -> str:
        return self.cache.get_redis_url()

    @property
    def CACHE_TTL_HOURS(self) -> int:
        return self.cache.CACHE_TTL_HOURS

    @property
    def RATE_LIMIT_ENABLED(self) -> bool:
        return self.app.RATE_LIMIT_ENABLED

    @property
    def ENABLE_DUPLICATE_DETECTION(self) -> bool:
        return self.cache.ENABLE_DUPLICATE_DETECTION

    @property
    def SIMILARITY_THRESHOLD(self) -> int:
        return self.cache.SIMILARITY_THRESHOLD

    @property
    def ALLOWED_ORIGINS(self) -> list:
        return self.app.ALLOWED_ORIGINS


# 加载环境配置
def initialize_config(environment: str = None) -> Settings:
    """
    初始化配置

    Args:
        environment: 环境名称，如果不指定则从环境变量获取

    Returns:
        Settings: 配置实例
    """
    # 加载环境配置文件
    try:
        config_loader.load_environment_config(environment)
    except Exception as e:
        print(f"Warning: Could not load environment config: {e}")
        print("Using environment variables or default values")

    # 创建配置实例
    config_instance = Settings()

    # 验证所有配置
    try:
        config_instance.validate_all()
    except Exception as e:
        print(f"Configuration validation error: {e}")
        # 在开发环境中，可以选择继续运行
        # 在生产环境中，应该停止应用启动
        if os.getenv("ENVIRONMENT", "development") == "production":
            raise

    return config_instance


# 创建全局配置实例
settings = initialize_config()


def get_settings() -> Settings:
    """Get global settings instance"""
    return settings
