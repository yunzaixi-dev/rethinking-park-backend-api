"""
外部服务配置

管理外部服务配置，如Google Cloud、监控服务等。
"""

from typing import Any, Dict, Optional

from .base import BaseConfig, ConfigValidationError


class ExternalServicesConfig(BaseConfig):
    """外部服务配置类"""

    def __init__(self):
        # Google Cloud配置
        self.GOOGLE_CLOUD_PROJECT_ID: str = ""
        self.GOOGLE_CLOUD_STORAGE_BUCKET: str = ""
        self.GOOGLE_APPLICATION_CREDENTIALS: str = ""
        self.GOOGLE_CLOUD_REGION: str = "us-central1"

        # Google Vision API配置
        self.GOOGLE_VISION_ENABLED: bool = True
        self.GOOGLE_VISION_MAX_RESULTS: int = 10
        self.GOOGLE_VISION_TIMEOUT: int = 30

        # 监控配置
        self.MONITORING_ENABLED: bool = True
        self.PROMETHEUS_ENABLED: bool = False
        self.PROMETHEUS_PORT: int = 8000
        self.METRICS_ENDPOINT: str = "/metrics"

        # 日志配置
        self.LOG_LEVEL: str = "INFO"
        self.LOG_FORMAT: str = "json"
        self.LOG_FILE: Optional[str] = None
        self.LOG_MAX_SIZE: int = 100 * 1024 * 1024  # 100MB
        self.LOG_BACKUP_COUNT: int = 5

        # 健康检查配置
        self.HEALTH_CHECK_ENABLED: bool = True
        self.HEALTH_CHECK_ENDPOINT: str = "/health"
        self.HEALTH_CHECK_TIMEOUT: int = 5

        # 外部API配置
        self.EXTERNAL_API_TIMEOUT: int = 30
        self.EXTERNAL_API_RETRIES: int = 3
        self.EXTERNAL_API_BACKOFF_FACTOR: float = 0.3

        # Webhook配置
        self.WEBHOOK_ENABLED: bool = False
        self.WEBHOOK_URL: Optional[str] = None
        self.WEBHOOK_SECRET: Optional[str] = None
        self.WEBHOOK_TIMEOUT: int = 10

        super().__init__()

    def load_config(self) -> None:
        """从环境变量加载配置"""
        # Google Cloud配置
        self.GOOGLE_CLOUD_PROJECT_ID = self.get_env_str(
            "GOOGLE_CLOUD_PROJECT_ID", self.GOOGLE_CLOUD_PROJECT_ID
        )
        self.GOOGLE_CLOUD_STORAGE_BUCKET = self.get_env_str(
            "GOOGLE_CLOUD_STORAGE_BUCKET", self.GOOGLE_CLOUD_STORAGE_BUCKET
        )
        self.GOOGLE_APPLICATION_CREDENTIALS = self.get_env_str(
            "GOOGLE_APPLICATION_CREDENTIALS", self.GOOGLE_APPLICATION_CREDENTIALS
        )
        self.GOOGLE_CLOUD_REGION = self.get_env_str(
            "GOOGLE_CLOUD_REGION", self.GOOGLE_CLOUD_REGION
        )

        # Google Vision API配置
        self.GOOGLE_VISION_ENABLED = self.get_env_bool(
            "GOOGLE_VISION_ENABLED", self.GOOGLE_VISION_ENABLED
        )
        self.GOOGLE_VISION_MAX_RESULTS = self.get_env_int(
            "GOOGLE_VISION_MAX_RESULTS", self.GOOGLE_VISION_MAX_RESULTS
        )
        self.GOOGLE_VISION_TIMEOUT = self.get_env_int(
            "GOOGLE_VISION_TIMEOUT", self.GOOGLE_VISION_TIMEOUT
        )

        # 监控配置
        self.MONITORING_ENABLED = self.get_env_bool(
            "MONITORING_ENABLED", self.MONITORING_ENABLED
        )
        self.PROMETHEUS_ENABLED = self.get_env_bool(
            "PROMETHEUS_ENABLED", self.PROMETHEUS_ENABLED
        )
        self.PROMETHEUS_PORT = self.get_env_int("PROMETHEUS_PORT", self.PROMETHEUS_PORT)
        self.METRICS_ENDPOINT = self.get_env_str(
            "METRICS_ENDPOINT", self.METRICS_ENDPOINT
        )

        # 日志配置
        self.LOG_LEVEL = self.get_env_str("LOG_LEVEL", self.LOG_LEVEL)
        self.LOG_FORMAT = self.get_env_str("LOG_FORMAT", self.LOG_FORMAT)
        self.LOG_FILE = self.get_env_str("LOG_FILE") or None
        self.LOG_MAX_SIZE = self.get_env_int("LOG_MAX_SIZE", self.LOG_MAX_SIZE)
        self.LOG_BACKUP_COUNT = self.get_env_int(
            "LOG_BACKUP_COUNT", self.LOG_BACKUP_COUNT
        )

        # 健康检查配置
        self.HEALTH_CHECK_ENABLED = self.get_env_bool(
            "HEALTH_CHECK_ENABLED", self.HEALTH_CHECK_ENABLED
        )
        self.HEALTH_CHECK_ENDPOINT = self.get_env_str(
            "HEALTH_CHECK_ENDPOINT", self.HEALTH_CHECK_ENDPOINT
        )
        self.HEALTH_CHECK_TIMEOUT = self.get_env_int(
            "HEALTH_CHECK_TIMEOUT", self.HEALTH_CHECK_TIMEOUT
        )

        # 外部API配置
        self.EXTERNAL_API_TIMEOUT = self.get_env_int(
            "EXTERNAL_API_TIMEOUT", self.EXTERNAL_API_TIMEOUT
        )
        self.EXTERNAL_API_RETRIES = self.get_env_int(
            "EXTERNAL_API_RETRIES", self.EXTERNAL_API_RETRIES
        )
        self.EXTERNAL_API_BACKOFF_FACTOR = float(
            self.get_env_str(
                "EXTERNAL_API_BACKOFF_FACTOR", str(self.EXTERNAL_API_BACKOFF_FACTOR)
            )
        )

        # Webhook配置
        self.WEBHOOK_ENABLED = self.get_env_bool(
            "WEBHOOK_ENABLED", self.WEBHOOK_ENABLED
        )
        self.WEBHOOK_URL = self.get_env_str("WEBHOOK_URL") or None
        self.WEBHOOK_SECRET = self.get_env_str("WEBHOOK_SECRET") or None
        self.WEBHOOK_TIMEOUT = self.get_env_int("WEBHOOK_TIMEOUT", self.WEBHOOK_TIMEOUT)

    def validate_config(self) -> None:
        """验证配置"""
        # Google Cloud配置验证
        if self.GOOGLE_VISION_ENABLED:
            if not self.GOOGLE_CLOUD_PROJECT_ID:
                raise ConfigValidationError(
                    "GOOGLE_CLOUD_PROJECT_ID is required when Google Vision is enabled"
                )

            if not self.GOOGLE_APPLICATION_CREDENTIALS:
                raise ConfigValidationError(
                    "GOOGLE_APPLICATION_CREDENTIALS is required when Google Vision is enabled"
                )

        if self.GOOGLE_VISION_MAX_RESULTS <= 0:
            raise ConfigValidationError("GOOGLE_VISION_MAX_RESULTS must be positive")

        if self.GOOGLE_VISION_TIMEOUT <= 0:
            raise ConfigValidationError("GOOGLE_VISION_TIMEOUT must be positive")

        # 监控配置验证
        if self.PROMETHEUS_ENABLED:
            if self.PROMETHEUS_PORT <= 0 or self.PROMETHEUS_PORT > 65535:
                raise ConfigValidationError(
                    "PROMETHEUS_PORT must be between 1 and 65535"
                )

        # 日志配置验证
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            raise ConfigValidationError(f"LOG_LEVEL must be one of: {valid_log_levels}")

        valid_log_formats = ["json", "text"]
        if self.LOG_FORMAT.lower() not in valid_log_formats:
            raise ConfigValidationError(
                f"LOG_FORMAT must be one of: {valid_log_formats}"
            )

        if self.LOG_MAX_SIZE <= 0:
            raise ConfigValidationError("LOG_MAX_SIZE must be positive")

        if self.LOG_BACKUP_COUNT < 0:
            raise ConfigValidationError("LOG_BACKUP_COUNT must be non-negative")

        # 健康检查配置验证
        if self.HEALTH_CHECK_TIMEOUT <= 0:
            raise ConfigValidationError("HEALTH_CHECK_TIMEOUT must be positive")

        # 外部API配置验证
        if self.EXTERNAL_API_TIMEOUT <= 0:
            raise ConfigValidationError("EXTERNAL_API_TIMEOUT must be positive")

        if self.EXTERNAL_API_RETRIES < 0:
            raise ConfigValidationError("EXTERNAL_API_RETRIES must be non-negative")

        if self.EXTERNAL_API_BACKOFF_FACTOR < 0:
            raise ConfigValidationError(
                "EXTERNAL_API_BACKOFF_FACTOR must be non-negative"
            )

        # Webhook配置验证
        if self.WEBHOOK_ENABLED:
            if not self.WEBHOOK_URL:
                raise ConfigValidationError(
                    "WEBHOOK_URL is required when webhooks are enabled"
                )

        if self.WEBHOOK_TIMEOUT <= 0:
            raise ConfigValidationError("WEBHOOK_TIMEOUT must be positive")

    def get_google_credentials_path(self) -> Optional[str]:
        """获取Google凭证文件路径"""
        return (
            self.GOOGLE_APPLICATION_CREDENTIALS
            if self.GOOGLE_APPLICATION_CREDENTIALS
            else None
        )

    def is_google_cloud_configured(self) -> bool:
        """检查Google Cloud是否已配置"""
        return bool(
            self.GOOGLE_CLOUD_PROJECT_ID and self.GOOGLE_APPLICATION_CREDENTIALS
        )

    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return {
            "enabled": self.MONITORING_ENABLED,
            "prometheus": {
                "enabled": self.PROMETHEUS_ENABLED,
                "port": self.PROMETHEUS_PORT,
                "endpoint": self.METRICS_ENDPOINT,
            },
        }
