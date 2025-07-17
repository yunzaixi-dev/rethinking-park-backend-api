"""
Base model classes and common functionality.

This module provides the foundation for all models in the application,
including base classes, mixins, and common utilities with enhanced
validation, serialization, and documentation capabilities.
"""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel as PydanticBaseModel
from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# Type variable for generic models
T = TypeVar("T")


class SerializationFormat(str, Enum):
    """Supported serialization formats."""

    JSON = "json"
    DICT = "dict"
    XML = "xml"


class TimestampMixin(PydanticBaseModel):
    """Mixin for models that need timestamp fields."""

    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


class BaseModel(PydanticBaseModel):
    """
    Enhanced base model class for all application models.

    Provides comprehensive functionality including:
    - Advanced validation and type checking
    - Multiple serialization formats
    - Schema generation and documentation
    - Data transformation utilities
    - Comparison and hashing operations
    """

    model_config = ConfigDict(
        # Enable validation on assignment
        validate_assignment=True,
        # Use enum values instead of enum objects
        use_enum_values=True,
        # Allow population by field name or alias
        populate_by_name=True,
        # Validate default values
        validate_default=True,
        # Extra fields are forbidden by default
        extra="forbid",
        # Enable JSON schema generation
        json_schema_serialization_defaults_required=True,
        # Enable arbitrary types for complex objects
        arbitrary_types_allowed=True,
        # Validate return values from methods
        validate_return=True,
    )

    def to_dict(
        self,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        include_private: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert model to dictionary with advanced options.

        Args:
            exclude_none: Exclude fields with None values
            exclude_unset: Exclude fields that were not explicitly set
            include_private: Include private fields (starting with _)

        Returns:
            Dict[str, Any]: Model as dictionary
        """
        return self.model_dump(
            exclude_none=exclude_none, exclude_unset=exclude_unset, by_alias=True
        )

    def to_json(
        self,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        indent: Optional[int] = None,
    ) -> str:
        """
        Convert model to JSON string with formatting options.

        Args:
            exclude_none: Exclude fields with None values
            exclude_unset: Exclude fields that were not explicitly set
            indent: JSON indentation level

        Returns:
            str: Model as JSON string
        """
        return self.model_dump_json(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            by_alias=True,
            indent=indent,
        )

    def to_xml(self) -> str:
        """
        Convert model to XML string.

        Returns:
            str: Model as XML string
        """
        # Simple XML conversion - can be enhanced with proper XML library
        data = self.to_dict(exclude_none=True)
        xml_parts = [f"<{self.__class__.__name__}>"]

        for key, value in data.items():
            if isinstance(value, (dict, list)):
                # For complex types, convert to JSON string
                value = json.dumps(value)
            xml_parts.append(f"  <{key}>{value}</{key}>")

        xml_parts.append(f"</{self.__class__.__name__}>")
        return "\n".join(xml_parts)

    def serialize(
        self, format_type: SerializationFormat = SerializationFormat.DICT
    ) -> Union[Dict, str]:
        """
        Serialize model to specified format.

        Args:
            format_type: Target serialization format

        Returns:
            Union[Dict, str]: Serialized model
        """
        if format_type == SerializationFormat.DICT:
            return self.to_dict()
        elif format_type == SerializationFormat.JSON:
            return self.to_json()
        elif format_type == SerializationFormat.XML:
            return self.to_xml()
        else:
            raise ValueError(f"Unsupported serialization format: {format_type}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """
        Create model instance from dictionary with validation.

        Args:
            data: Dictionary data

        Returns:
            BaseModel: Model instance

        Raises:
            ValidationError: If data is invalid
        """
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> "BaseModel":
        """
        Create model instance from JSON string with validation.

        Args:
            json_str: JSON string

        Returns:
            BaseModel: Model instance

        Raises:
            ValidationError: If JSON is invalid
        """
        return cls.model_validate_json(json_str)

    @classmethod
    def get_schema(cls, by_alias: bool = True) -> Dict[str, Any]:
        """
        Get JSON schema for the model.

        Args:
            by_alias: Use field aliases in schema

        Returns:
            Dict[str, Any]: JSON schema
        """
        return cls.model_json_schema(by_alias=by_alias)

    @classmethod
    def get_field_info(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about model fields.

        Returns:
            Dict[str, Dict[str, Any]]: Field information
        """
        field_info = {}
        for field_name, field in cls.model_fields.items():
            field_info[field_name] = {
                "type": str(field.annotation),
                "required": field.is_required(),
                "default": field.default if field.default is not None else None,
                "description": field.description,
                "constraints": getattr(field, "constraints", {}),
            }
        return field_info

    def get_changed_fields(self, other: "BaseModel") -> Dict[str, tuple[Any, Any]]:
        """
        Compare with another model instance and get changed fields.

        Args:
            other: Other model instance to compare with

        Returns:
            Dict[str, tuple[Any, Any]]: Changed fields with (old, new) values
        """
        if not isinstance(other, self.__class__):
            raise ValueError("Can only compare with same model type")

        changes = {}
        self_dict = self.to_dict()
        other_dict = other.to_dict()

        for key in self_dict:
            if key in other_dict and self_dict[key] != other_dict[key]:
                changes[key] = (other_dict[key], self_dict[key])

        return changes

    def copy_with_changes(self, **changes) -> "BaseModel":
        """
        Create a copy of the model with specified changes.

        Args:
            **changes: Fields to change

        Returns:
            BaseModel: New model instance with changes
        """
        data = self.to_dict()
        data.update(changes)
        return self.__class__.from_dict(data)

    def validate_model(self) -> List[str]:
        """
        Validate the model and return list of validation errors.

        Returns:
            List[str]: List of validation error messages
        """
        try:
            self.model_validate(self.to_dict())
            return []
        except Exception as e:
            return [str(e)]

    def __hash__(self) -> int:
        """Generate hash for the model based on its data."""
        return hash(self.to_json())

    def __eq__(self, other) -> bool:
        """Check equality with another model instance."""
        if not isinstance(other, self.__class__):
            return False
        return self.to_dict() == other.to_dict()


class BaseRequest(BaseModel):
    """
    Base class for all request models.

    Provides common functionality for API request models.
    """

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="请求唯一标识符"
    )

    def validate_request(self) -> bool:
        """
        Validate the request data.

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            self.model_validate(self.model_dump())
            return True
        except Exception:
            return False


class BaseResponse(BaseModel):
    """
    Base class for all response models.

    Provides common functionality for API response models.
    """

    success: bool = Field(default=True, description="操作是否成功")
    message: Optional[str] = Field(default=None, description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

    @classmethod
    def success_response(
        cls, data: Optional[Dict[str, Any]] = None, message: Optional[str] = None
    ) -> "BaseResponse":
        """Create a success response."""
        response_data = {
            "success": True,
            "message": message or "操作成功",
            "timestamp": datetime.now(),
        }
        if data:
            response_data.update(data)
        return cls(**response_data)

    @classmethod
    def error_response(
        cls, message: str, error_details: Optional[Dict[str, Any]] = None
    ) -> "BaseResponse":
        """Create an error response."""
        response_data = {
            "success": False,
            "message": message,
            "timestamp": datetime.now(),
        }
        if error_details:
            response_data["error_details"] = error_details
        return cls(**response_data)


class PaginatedRequest(BaseRequest):
    """Base class for paginated requests."""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseResponse, Generic[T]):
    """Base class for paginated responses."""

    items: list[T] = Field(default=[], description="数据项列表")
    total: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
    total_pages: int = Field(default=0, description="总页数")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
        message: Optional[str] = None,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            success=True,
            message=message or "查询成功",
        )


class ErrorResponse(BaseResponse):
    """Standard error response model."""

    error_code: Optional[str] = Field(default=None, description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="错误详情"
    )

    def __init__(self, **data):
        # Ensure success is False for error responses
        data["success"] = False
        super().__init__(**data)


class ValidationErrorResponse(ErrorResponse):
    """Validation error response model."""

    validation_errors: list[Dict[str, Any]] = Field(
        default=[], description="验证错误详情"
    )


# Abstract base classes for domain models
class DomainModel(BaseModel, TimestampMixin, ABC):
    """
    Abstract base class for domain models.

    Combines BaseModel with timestamp functionality and
    provides abstract methods for domain-specific operations.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="唯一标识符")

    @abstractmethod
    def validate_business_rules(self) -> bool:
        """
        Validate business rules for this domain model.

        Returns:
            bool: True if all business rules are satisfied
        """
        pass

    @abstractmethod
    def get_display_name(self) -> str:
        """
        Get a human-readable display name for this model.

        Returns:
            str: Display name
        """
        pass


class AuditMixin(PydanticBaseModel):
    """Mixin for models that need audit trail functionality."""

    created_by: Optional[str] = Field(default=None, description="创建者")
    updated_by: Optional[str] = Field(default=None, description="更新者")
    version: int = Field(default=1, description="版本号")

    def increment_version(self, updated_by: Optional[str] = None) -> None:
        """Increment version and update audit fields."""
        self.version += 1
        self.updated_by = updated_by
        if hasattr(self, "update_timestamp"):
            self.update_timestamp()


class SoftDeleteMixin(PydanticBaseModel):
    """Mixin for models that support soft deletion."""

    is_deleted: bool = Field(default=False, description="是否已删除")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")
    deleted_by: Optional[str] = Field(default=None, description="删除者")

    def soft_delete(self, deleted_by: Optional[str] = None) -> None:
        """Perform soft deletion."""
        self.is_deleted = True
        self.deleted_at = datetime.now()
        self.deleted_by = deleted_by

    def restore(self) -> None:
        """Restore from soft deletion."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
