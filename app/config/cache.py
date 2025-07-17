"""
缓存配置

管理缓存相关配置，包括Redis、内存缓存等配置。
"""

from typing import Optional

from .base import BaseConfig, ConfigValidationError


class CacheConfig(BaseConfig):
    """缓存配置类"""

    def __init__(self):
        # Redis配置
        self.REDIS_ENABLED: bool = True
        self.REDIS_URL: str = "redis://localhost:6379"
        self.REDIS_HOST: str = "localhost"
        self.REDIS_PORT: int = 6379
        self.REDIS_DB: int = 0
        self.REDIS_PASSWORD: Optional[str] = None
        self.REDIS_USERNAME: Optional[str] = None

        # Redis连接池配置
        self.REDIS_MAX_CONNECTIONS: int = 10
        self.REDIS_RETRY_ON_TIMEOUT: bool = True
        self.REDIS_SOCKET_TIMEOUT: int = 5
        self.REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

        # 缓存TTL配置
        self.CACHE_TTL_HOURS: int = 24
        self.CACHE_TTL_SECONDS: int = 86400  # 24小时
        self.SHORT_CACHE_TTL_SECONDS: int = 300  # 5分钟
        self.LONG_CACHE_TTL_SECONDS: int = 604800  # 7天

        # 内存缓存配置
        self.MEMORY_CACHE_ENABLED: bool = True
        self.MEMORY_CACHE_MAX_SIZE: int = 1000
        self.MEMORY_CACHE_TTL_SECONDS: int = 300

        # 缓存键前缀
        self.CACHE_KEY_PREFIX: str = "rethinking_park"

        # 图像哈希缓存配置
        self.ENABLE_DUPLICATE_DETECTION: bool = True
        self.SIMILARITY_THRESHOLD: int = 5  # 汉明距离阈值

        super().__init__()

    def load_config(self) -> None:
        """从环境变量加载配置"""
        # Redis基本配置
        self.REDIS_ENABLED = self.get_env_bool("REDIS_ENABLED", self.REDIS_ENABLED)
        self.REDIS_URL = self.get_env_str("REDIS_URL", self.REDIS_URL)
        self.REDIS_HOST = self.get_env_str("REDIS_HOST", self.REDIS_HOST)
        self.REDIS_PORT = self.get_env_int("REDIS_PORT", self.REDIS_PORT)
        self.REDIS_DB = self.get_env_int("REDIS_DB", self.REDIS_DB)
        self.REDIS_PASSWORD = self.get_env_str("REDIS_PASSWORD") or None
        self.REDIS_USERNAME = self.get_env_str("REDIS_USERNAME") or None

        # Redis连接池配置
        self.REDIS_MAX_CONNECTIONS = self.get_env_int(
            "REDIS_MAX_CONNECTIONS", self.REDIS_MAX_CONNECTIONS
        )
        self.REDIS_RETRY_ON_TIMEOUT = self.get_env_bool(
            "REDIS_RETRY_ON_TIMEOUT", self.REDIS_RETRY_ON_TIMEOUT
        )
        self.REDIS_SOCKET_TIMEOUT = self.get_env_int(
            "REDIS_SOCKET_TIMEOUT", self.REDIS_SOCKET_TIMEOUT
        )
        self.REDIS_SOCKET_CONNECT_TIMEOUT = self.get_env_int(
            "REDIS_SOCKET_CONNECT_TIMEOUT", self.REDIS_SOCKET_CONNECT_TIMEOUT
        )

        # 缓存TTL配置
        self.CACHE_TTL_HOURS = self.get_env_int("CACHE_TTL_HOURS", self.CACHE_TTL_HOURS)
        self.CACHE_TTL_SECONDS = self.get_env_int(
            "CACHE_TTL_SECONDS", self.CACHE_TTL_HOURS * 3600
        )
        self.SHORT_CACHE_TTL_SECONDS = self.get_env_int(
            "SHORT_CACHE_TTL_SECONDS", self.SHORT_CACHE_TTL_SECONDS
        )
        self.LONG_CACHE_TTL_SECONDS = self.get_env_int(
            "LONG_CACHE_TTL_SECONDS", self.LONG_CACHE_TTL_SECONDS
        )

        # 内存缓存配置
        self.MEMORY_CACHE_ENABLED = self.get_env_bool(
            "MEMORY_CACHE_ENABLED", self.MEMORY_CACHE_ENABLED
        )
        self.MEMORY_CACHE_MAX_SIZE = self.get_env_int(
            "MEMORY_CACHE_MAX_SIZE", self.MEMORY_CACHE_MAX_SIZE
        )
        self.MEMORY_CACHE_TTL_SECONDS = self.get_env_int(
            "MEMORY_CACHE_TTL_SECONDS", self.MEMORY_CACHE_TTL_SECONDS
        )

        # 缓存键前缀
        self.CACHE_KEY_PREFIX = self.get_env_str(
            "CACHE_KEY_PREFIX", self.CACHE_KEY_PREFIX
        )

        # 图像哈希配置
        self.ENABLE_DUPLICATE_DETECTION = self.get_env_bool(
            "ENABLE_DUPLICATE_DETECTION", self.ENABLE_DUPLICATE_DETECTION
        )
        self.SIMILARITY_THRESHOLD = self.get_env_int(
            "SIMILARITY_THRESHOLD", self.SIMILARITY_THRESHOLD
        )

    def validate_config(self) -> None:
        """验证配置"""
        if self.REDIS_ENABLED:
            if self.REDIS_PORT <= 0 or self.REDIS_PORT > 65535:
                raise ConfigValidationError("REDIS_PORT must be between 1 and 65535")

            if self.REDIS_DB < 0:
                raise ConfigValidationError("REDIS_DB must be non-negative")

            if self.REDIS_MAX_CONNECTIONS <= 0:
                raise ConfigValidationError("REDIS_MAX_CONNECTIONS must be positive")

            if self.REDIS_SOCKET_TIMEOUT <= 0:
                raise ConfigValidationError("REDIS_SOCKET_TIMEOUT must be positive")

            if self.REDIS_SOCKET_CONNECT_TIMEOUT <= 0:
                raise ConfigValidationError(
                    "REDIS_SOCKET_CONNECT_TIMEOUT must be positive"
                )

        if self.CACHE_TTL_SECONDS <= 0:
            raise ConfigValidationError("CACHE_TTL_SECONDS must be positive")

        if self.SHORT_CACHE_TTL_SECONDS <= 0:
            raise ConfigValidationError("SHORT_CACHE_TTL_SECONDS must be positive")

        if self.LONG_CACHE_TTL_SECONDS <= 0:
            raise ConfigValidationError("LONG_CACHE_TTL_SECONDS must be positive")

        if self.MEMORY_CACHE_ENABLED:
            if self.MEMORY_CACHE_MAX_SIZE <= 0:
                raise ConfigValidationError("MEMORY_CACHE_MAX_SIZE must be positive")

            if self.MEMORY_CACHE_TTL_SECONDS <= 0:
                raise ConfigValidationError("MEMORY_CACHE_TTL_SECONDS must be positive")

        if self.SIMILARITY_THRESHOLD < 0:
            raise ConfigValidationError("SIMILARITY_THRESHOLD must be non-negative")

        if not self.CACHE_KEY_PREFIX:
            raise ConfigValidationError("CACHE_KEY_PREFIX cannot be empty")

    def get_redis_url(self) -> str:
        """获取Redis连接URL"""
        if self.REDIS_URL and "://" in self.REDIS_URL:
            return self.REDIS_URL

        # 构建Redis URL
        auth_part = ""
        if self.REDIS_USERNAME and self.REDIS_PASSWORD:
            auth_part = f"{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@"
        elif self.REDIS_PASSWORD:
            auth_part = f":{self.REDIS_PASSWORD}@"

        return f"redis://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def get_cache_key(self, key: str) -> str:
        """获取带前缀的缓存键"""
        return f"{self.CACHE_KEY_PREFIX}:{key}"
