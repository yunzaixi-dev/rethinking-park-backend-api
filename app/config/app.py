"""
应用配置

管理应用基本配置，如应用名称、版本、调试模式等。
"""

from typing import List

from .base import BaseConfig, ConfigValidationError


class AppConfig(BaseConfig):
    """应用配置类"""

    def __init__(self):
        # 默认值
        self.APP_NAME: str = "Rethinking Park Backend API"
        self.APP_VERSION: str = "2.0.0"
        self.DEBUG: bool = False
        self.API_V1_STR: str = "/api/v1"
        self.ENVIRONMENT: str = "development"

        # 文件上传配置
        self.MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
        self.ALLOWED_IMAGE_EXTENSIONS: List[str] = [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp",
        ]

        # CORS配置
        self.ALLOWED_ORIGINS: List[str] = ["*"]
        self.ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.ALLOWED_HEADERS: List[str] = ["*"]

        # 速率限制配置
        self.RATE_LIMIT_ENABLED: bool = True
        self.RATE_LIMIT_REQUESTS: int = 100
        self.RATE_LIMIT_WINDOW: int = 3600  # 1小时

        super().__init__()

    def load_config(self) -> None:
        """从环境变量加载配置"""
        self.APP_NAME = self.get_env_str("APP_NAME", self.APP_NAME)
        self.APP_VERSION = self.get_env_str("APP_VERSION", self.APP_VERSION)
        self.DEBUG = self.get_env_bool("DEBUG", self.DEBUG)
        self.API_V1_STR = self.get_env_str("API_V1_STR", self.API_V1_STR)
        self.ENVIRONMENT = self.get_env_str("ENVIRONMENT", self.ENVIRONMENT)

        # 文件上传配置
        self.MAX_UPLOAD_SIZE = self.get_env_int("MAX_UPLOAD_SIZE", self.MAX_UPLOAD_SIZE)

        # CORS配置
        allowed_origins = self.get_env_str("ALLOWED_ORIGINS", "*")
        if allowed_origins == "*":
            self.ALLOWED_ORIGINS = ["*"]
        else:
            self.ALLOWED_ORIGINS = self.get_env_list(
                "ALLOWED_ORIGINS", self.ALLOWED_ORIGINS
            )

        self.ALLOWED_METHODS = self.get_env_list(
            "ALLOWED_METHODS", self.ALLOWED_METHODS
        )
        self.ALLOWED_HEADERS = self.get_env_list(
            "ALLOWED_HEADERS", self.ALLOWED_HEADERS
        )

        # 速率限制配置
        self.RATE_LIMIT_ENABLED = self.get_env_bool(
            "RATE_LIMIT_ENABLED", self.RATE_LIMIT_ENABLED
        )
        self.RATE_LIMIT_REQUESTS = self.get_env_int(
            "RATE_LIMIT_REQUESTS", self.RATE_LIMIT_REQUESTS
        )
        self.RATE_LIMIT_WINDOW = self.get_env_int(
            "RATE_LIMIT_WINDOW", self.RATE_LIMIT_WINDOW
        )

    def validate_config(self) -> None:
        """验证配置"""
        if not self.APP_NAME:
            raise ConfigValidationError("APP_NAME cannot be empty")

        if not self.APP_VERSION:
            raise ConfigValidationError("APP_VERSION cannot be empty")

        if self.MAX_UPLOAD_SIZE <= 0:
            raise ConfigValidationError("MAX_UPLOAD_SIZE must be positive")

        if self.RATE_LIMIT_REQUESTS <= 0:
            raise ConfigValidationError("RATE_LIMIT_REQUESTS must be positive")

        if self.RATE_LIMIT_WINDOW <= 0:
            raise ConfigValidationError("RATE_LIMIT_WINDOW must be positive")

        # 验证环境类型
        valid_environments = ["development", "staging", "production", "testing"]
        if self.ENVIRONMENT not in valid_environments:
            raise ConfigValidationError(
                f"ENVIRONMENT must be one of: {valid_environments}"
            )

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.ENVIRONMENT == "testing"
