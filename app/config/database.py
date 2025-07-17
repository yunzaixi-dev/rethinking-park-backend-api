"""
数据库配置

管理数据库连接配置，包括主数据库、读写分离、连接池等配置。
"""

from typing import Optional

from .base import BaseConfig, ConfigValidationError


class DatabaseConfig(BaseConfig):
    """数据库配置类"""

    def __init__(self):
        # 主数据库配置
        self.DATABASE_URL: Optional[str] = None
        self.DATABASE_HOST: str = "localhost"
        self.DATABASE_PORT: int = 5432
        self.DATABASE_NAME: str = "rethinking_park"
        self.DATABASE_USER: str = "postgres"
        self.DATABASE_PASSWORD: str = ""

        # 连接池配置
        self.DATABASE_POOL_SIZE: int = 10
        self.DATABASE_MAX_OVERFLOW: int = 20
        self.DATABASE_POOL_TIMEOUT: int = 30
        self.DATABASE_POOL_RECYCLE: int = 3600

        # 读写分离配置
        self.READ_DATABASE_URL: Optional[str] = None
        self.ENABLE_READ_WRITE_SPLIT: bool = False

        # 其他配置
        self.DATABASE_ECHO: bool = False
        self.DATABASE_ECHO_POOL: bool = False

        super().__init__()

    def load_config(self) -> None:
        """从环境变量加载配置"""
        self.DATABASE_URL = self.get_env_str("DATABASE_URL")
        self.DATABASE_HOST = self.get_env_str("DATABASE_HOST", self.DATABASE_HOST)
        self.DATABASE_PORT = self.get_env_int("DATABASE_PORT", self.DATABASE_PORT)
        self.DATABASE_NAME = self.get_env_str("DATABASE_NAME", self.DATABASE_NAME)
        self.DATABASE_USER = self.get_env_str("DATABASE_USER", self.DATABASE_USER)
        self.DATABASE_PASSWORD = self.get_env_str(
            "DATABASE_PASSWORD", self.DATABASE_PASSWORD
        )

        # 连接池配置
        self.DATABASE_POOL_SIZE = self.get_env_int(
            "DATABASE_POOL_SIZE", self.DATABASE_POOL_SIZE
        )
        self.DATABASE_MAX_OVERFLOW = self.get_env_int(
            "DATABASE_MAX_OVERFLOW", self.DATABASE_MAX_OVERFLOW
        )
        self.DATABASE_POOL_TIMEOUT = self.get_env_int(
            "DATABASE_POOL_TIMEOUT", self.DATABASE_POOL_TIMEOUT
        )
        self.DATABASE_POOL_RECYCLE = self.get_env_int(
            "DATABASE_POOL_RECYCLE", self.DATABASE_POOL_RECYCLE
        )

        # 读写分离配置
        self.READ_DATABASE_URL = self.get_env_str("READ_DATABASE_URL")
        self.ENABLE_READ_WRITE_SPLIT = self.get_env_bool(
            "ENABLE_READ_WRITE_SPLIT", self.ENABLE_READ_WRITE_SPLIT
        )

        # 其他配置
        self.DATABASE_ECHO = self.get_env_bool("DATABASE_ECHO", self.DATABASE_ECHO)
        self.DATABASE_ECHO_POOL = self.get_env_bool(
            "DATABASE_ECHO_POOL", self.DATABASE_ECHO_POOL
        )

    def validate_config(self) -> None:
        """验证配置"""
        if not self.DATABASE_URL and not all(
            [self.DATABASE_HOST, self.DATABASE_NAME, self.DATABASE_USER]
        ):
            raise ConfigValidationError(
                "Either DATABASE_URL or DATABASE_HOST, DATABASE_NAME, DATABASE_USER must be provided"
            )

        if self.DATABASE_PORT <= 0 or self.DATABASE_PORT > 65535:
            raise ConfigValidationError("DATABASE_PORT must be between 1 and 65535")

        if self.DATABASE_POOL_SIZE <= 0:
            raise ConfigValidationError("DATABASE_POOL_SIZE must be positive")

        if self.DATABASE_MAX_OVERFLOW < 0:
            raise ConfigValidationError("DATABASE_MAX_OVERFLOW must be non-negative")

        if self.DATABASE_POOL_TIMEOUT <= 0:
            raise ConfigValidationError("DATABASE_POOL_TIMEOUT must be positive")

        if self.ENABLE_READ_WRITE_SPLIT and not self.READ_DATABASE_URL:
            raise ConfigValidationError(
                "READ_DATABASE_URL is required when ENABLE_READ_WRITE_SPLIT is True"
            )

    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL

        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    def get_read_database_url(self) -> Optional[str]:
        """获取读数据库连接URL"""
        if self.ENABLE_READ_WRITE_SPLIT and self.READ_DATABASE_URL:
            return self.READ_DATABASE_URL
        return None
