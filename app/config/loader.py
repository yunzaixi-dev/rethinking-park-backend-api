"""
配置加载器

支持从不同环境配置文件加载配置，并提供配置验证功能。
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from .base import ConfigValidationError


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录，默认为项目根目录下的config目录
        """
        if config_dir is None:
            # 获取项目根目录
            current_dir = Path(__file__).parent.parent.parent
            config_dir = current_dir / "config"

        self.config_dir = Path(config_dir)
        self.environment = os.getenv("ENVIRONMENT", "development")

    def load_environment_config(self, environment: Optional[str] = None) -> None:
        """
        加载指定环境的配置文件

        Args:
            environment: 环境名称，如果不指定则使用当前环境
        """
        if environment is None:
            environment = self.environment

        # 环境配置文件映射
        env_file_mapping = {
            "development": "local.env",
            "local": "local.env",
            "staging": "staging.env",
            "production": "production.env",
            "testing": "local.env",  # 测试环境使用本地配置
        }

        env_file = env_file_mapping.get(environment)
        if not env_file:
            raise ConfigValidationError(f"Unknown environment: {environment}")

        env_file_path = self.config_dir / env_file

        if not env_file_path.exists():
            raise ConfigValidationError(
                f"Environment config file not found: {env_file_path}"
            )

        # 加载环境配置文件
        load_dotenv(env_file_path, override=True)

        # 设置环境变量
        os.environ["ENVIRONMENT"] = environment

    def load_config_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        从字典加载配置

        Args:
            config_dict: 配置字典
        """
        for key, value in config_dict.items():
            os.environ[key] = str(value)

    def get_available_environments(self) -> list:
        """获取可用的环境列表"""
        return ["development", "local", "staging", "production", "testing"]

    def validate_environment(self, environment: str) -> bool:
        """
        验证环境是否有效

        Args:
            environment: 环境名称

        Returns:
            bool: 环境是否有效
        """
        return environment in self.get_available_environments()

    def get_config_file_path(self, environment: str) -> Path:
        """
        获取指定环境的配置文件路径

        Args:
            environment: 环境名称

        Returns:
            Path: 配置文件路径
        """
        env_file_mapping = {
            "development": "local.env",
            "local": "local.env",
            "staging": "staging.env",
            "production": "production.env",
            "testing": "local.env",
        }

        env_file = env_file_mapping.get(environment)
        if not env_file:
            raise ConfigValidationError(f"Unknown environment: {environment}")

        return self.config_dir / env_file

    def create_example_config(self, environment: str = "development") -> None:
        """
        创建示例配置文件

        Args:
            environment: 环境名称
        """
        config_file_path = self.get_config_file_path(environment)

        if config_file_path.exists():
            print(f"Config file already exists: {config_file_path}")
            return

        # 确保配置目录存在
        config_file_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建示例配置内容
        example_config = self._get_example_config_content(environment)

        with open(config_file_path, "w", encoding="utf-8") as f:
            f.write(example_config)

        print(f"Example config file created: {config_file_path}")

    def _get_example_config_content(self, environment: str) -> str:
        """获取示例配置内容"""
        return f"""# {environment.title()} Environment Configuration
# Please update the values according to your environment

# Application Configuration
APP_NAME=Rethinking Park Backend API
APP_VERSION=2.0.0
DEBUG={"true" if environment == "development" else "false"}
ENVIRONMENT={environment}
API_V1_STR=/api/v1

# Database Configuration
DATABASE_URL=
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=rethinking_park_{environment}
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password

# Redis Configuration
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# Add other configuration as needed...
"""


# 全局配置加载器实例
config_loader = ConfigLoader()


def load_config(environment: Optional[str] = None) -> None:
    """
    加载配置的便捷函数

    Args:
        environment: 环境名称
    """
    config_loader.load_environment_config(environment)
