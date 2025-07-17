"""
基础配置类

定义所有配置类的基础结构和通用功能。
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseConfig(ABC):
    """配置基类"""

    def __init__(self):
        self.load_config()
        self.validate_config()

    @abstractmethod
    def load_config(self) -> None:
        """加载配置"""
        pass

    @abstractmethod
    def validate_config(self) -> None:
        """验证配置"""
        pass

    def get_env_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔类型环境变量"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def get_env_int(self, key: str, default: int = 0) -> int:
        """获取整数类型环境变量"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default

    def get_env_list(
        self, key: str, default: Optional[List[str]] = None, separator: str = ","
    ) -> List[str]:
        """获取列表类型环境变量"""
        if default is None:
            default = []

        value = os.getenv(key, "")
        if not value:
            return default

        return [item.strip() for item in value.split(separator) if item.strip()]

    def get_env_str(self, key: str, default: str = "") -> str:
        """获取字符串类型环境变量"""
        return os.getenv(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        }


class ConfigValidationError(Exception):
    """配置验证错误"""

    pass
