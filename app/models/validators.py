"""
Custom validators for model fields.

This module provides custom validation functions and classes
for use with Pydantic models throughout the application.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationInfo, field_validator


class ValidationError(Exception):
    """Custom validation error."""

    pass


def validate_image_hash(value: str) -> str:
    """
    Validate image hash format (MD5).

    Args:
        value: Hash string to validate

    Returns:
        str: Validated hash string

    Raises:
        ValueError: If hash format is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Hash must be a string")

    # MD5 hash should be 32 hexadecimal characters
    if not re.match(r"^[a-fA-F0-9]{32}$", value):
        raise ValueError("Invalid MD5 hash format")

    return value.lower()


def validate_filename(value: str) -> str:
    """
    Validate filename format.

    Args:
        value: Filename to validate

    Returns:
        str: Validated filename

    Raises:
        ValueError: If filename is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Filename must be a string")

    if not value.strip():
        raise ValueError("Filename cannot be empty")

    # Check for invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    if re.search(invalid_chars, value):
        raise ValueError("Filename contains invalid characters")

    # Check length
    if len(value) > 255:
        raise ValueError("Filename too long (max 255 characters)")

    return value.strip()


def validate_content_type(value: str) -> str:
    """
    Validate MIME content type for images.

    Args:
        value: Content type to validate

    Returns:
        str: Validated content type

    Raises:
        ValueError: If content type is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Content type must be a string")

    valid_image_types = [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
        "image/svg+xml",
    ]

    if value.lower() not in valid_image_types:
        raise ValueError(f"Invalid image content type: {value}")

    return value.lower()


def validate_gcs_url(value: str) -> str:
    """
    Validate Google Cloud Storage URL format.

    Args:
        value: GCS URL to validate

    Returns:
        str: Validated GCS URL

    Raises:
        ValueError: If URL format is invalid
    """
    if not isinstance(value, str):
        raise ValueError("GCS URL must be a string")

    # Basic GCS URL pattern
    gcs_pattern = r"^https://storage\.googleapis\.com/[a-zA-Z0-9._-]+/.*$"
    if not re.match(gcs_pattern, value):
        raise ValueError("Invalid GCS URL format")

    return value


def validate_hex_color(value: str) -> str:
    """
    Validate hexadecimal color code.

    Args:
        value: Hex color code to validate

    Returns:
        str: Validated hex color code

    Raises:
        ValueError: If color code is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Hex color must be a string")

    # Remove # if present
    if value.startswith("#"):
        value = value[1:]

    # Validate hex format (3 or 6 characters)
    if not re.match(r"^[a-fA-F0-9]{3}$|^[a-fA-F0-9]{6}$", value):
        raise ValueError("Invalid hex color format")

    # Ensure 6-character format
    if len(value) == 3:
        value = "".join([c * 2 for c in value])

    return f"#{value.upper()}"


def validate_confidence_score(value: float) -> float:
    """
    Validate confidence score (0.0 to 1.0).

    Args:
        value: Confidence score to validate

    Returns:
        float: Validated confidence score

    Raises:
        ValueError: If score is out of range
    """
    if not isinstance(value, (int, float)):
        raise ValueError("Confidence score must be a number")

    if not 0.0 <= value <= 1.0:
        raise ValueError("Confidence score must be between 0.0 and 1.0")

    return float(value)


def validate_percentage(value: float) -> float:
    """
    Validate percentage value (0.0 to 100.0).

    Args:
        value: Percentage to validate

    Returns:
        float: Validated percentage

    Raises:
        ValueError: If percentage is out of range
    """
    if not isinstance(value, (int, float)):
        raise ValueError("Percentage must be a number")

    if not 0.0 <= value <= 100.0:
        raise ValueError("Percentage must be between 0.0 and 100.0")

    return float(value)


def validate_normalized_coordinate(value: float) -> float:
    """
    Validate normalized coordinate (0.0 to 1.0).

    Args:
        value: Coordinate to validate

    Returns:
        float: Validated coordinate

    Raises:
        ValueError: If coordinate is out of range
    """
    if not isinstance(value, (int, float)):
        raise ValueError("Coordinate must be a number")

    if not 0.0 <= value <= 1.0:
        raise ValueError("Normalized coordinate must be between 0.0 and 1.0")

    return float(value)


def validate_positive_integer(value: int) -> int:
    """
    Validate positive integer.

    Args:
        value: Integer to validate

    Returns:
        int: Validated integer

    Raises:
        ValueError: If integer is not positive
    """
    if not isinstance(value, int):
        raise ValueError("Value must be an integer")

    if value <= 0:
        raise ValueError("Value must be positive")

    return value


def validate_analysis_type(value: str) -> str:
    """
    Validate analysis type.

    Args:
        value: Analysis type to validate

    Returns:
        str: Validated analysis type

    Raises:
        ValueError: If analysis type is invalid
    """
    valid_types = [
        "labels",
        "objects",
        "faces",
        "text",
        "landmarks",
        "natural_elements",
        "enhanced_detection",
        "label_analysis",
    ]

    if value not in valid_types:
        raise ValueError(f"Invalid analysis type: {value}")

    return value


def validate_health_status(value: str) -> str:
    """
    Validate vegetation health status.

    Args:
        value: Health status to validate

    Returns:
        str: Validated health status

    Raises:
        ValueError: If health status is invalid
    """
    valid_statuses = ["healthy", "moderate", "poor", "unknown"]

    if value not in valid_statuses:
        raise ValueError(f"Invalid health status: {value}")

    return value


def validate_season(value: str) -> str:
    """
    Validate season name.

    Args:
        value: Season to validate

    Returns:
        str: Validated season

    Raises:
        ValueError: If season is invalid
    """
    valid_seasons = ["spring", "summer", "autumn", "winter"]

    if value.lower() not in valid_seasons:
        raise ValueError(f"Invalid season: {value}")

    return value.lower()


def validate_batch_operation_type(value: str) -> str:
    """
    Validate batch operation type.

    Args:
        value: Operation type to validate

    Returns:
        str: Validated operation type

    Raises:
        ValueError: If operation type is invalid
    """
    valid_types = [
        "detect_objects",
        "extract_object",
        "analyze_labels",
        "analyze_nature",
        "annotate_image",
    ]

    if value not in valid_types:
        raise ValueError(f"Invalid batch operation type: {value}")

    return value


def validate_batch_status(value: str) -> str:
    """
    Validate batch operation status.

    Args:
        value: Status to validate

    Returns:
        str: Validated status

    Raises:
        ValueError: If status is invalid
    """
    valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]

    if value not in valid_statuses:
        raise ValueError(f"Invalid batch status: {value}")

    return value


class ModelValidator:
    """
    Utility class for complex model validation.
    """

    @staticmethod
    def validate_bounding_box_coordinates(bbox_data: Dict[str, float]) -> bool:
        """
        Validate that bounding box coordinates are consistent.

        Args:
            bbox_data: Dictionary with x, y, width, height

        Returns:
            bool: True if coordinates are valid
        """
        x, y, width, height = (
            bbox_data["x"],
            bbox_data["y"],
            bbox_data["width"],
            bbox_data["height"],
        )

        # Check that box doesn't exceed image boundaries
        if x + width > 1.0 or y + height > 1.0:
            return False

        # Check minimum size
        if width < 0.001 or height < 0.001:
            return False

        return True

    @staticmethod
    def validate_color_components(red: float, green: float, blue: float) -> bool:
        """
        Validate RGB color components.

        Args:
            red: Red component (0-255)
            green: Green component (0-255)
            blue: Blue component (0-255)

        Returns:
            bool: True if components are valid
        """
        return all(0 <= component <= 255 for component in [red, green, blue])

    @staticmethod
    def validate_image_dimensions(width: int, height: int) -> bool:
        """
        Validate image dimensions.

        Args:
            width: Image width
            height: Image height

        Returns:
            bool: True if dimensions are valid
        """
        # Check minimum dimensions
        if width < 1 or height < 1:
            return False

        # Check maximum dimensions (reasonable limits)
        max_dimension = 50000  # 50k pixels
        if width > max_dimension or height > max_dimension:
            return False

        return True

    @staticmethod
    def validate_analysis_results(results: Dict[str, Any], analysis_type: str) -> bool:
        """
        Validate analysis results structure based on type.

        Args:
            results: Analysis results dictionary
            analysis_type: Type of analysis

        Returns:
            bool: True if results structure is valid
        """
        if not isinstance(results, dict):
            return False

        # Type-specific validation
        if analysis_type == "labels":
            return "labels" in results and isinstance(results["labels"], list)
        elif analysis_type == "faces":
            return "faces" in results and isinstance(results["faces"], list)
        elif analysis_type == "natural_elements":
            required_keys = ["vegetation_coverage", "sky_coverage", "water_coverage"]
            return all(key in results for key in required_keys)

        return True  # Basic validation passed
