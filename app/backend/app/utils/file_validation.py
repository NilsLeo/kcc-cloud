"""
File validation utilities for manga converter.

This module provides validation functions for file uploads, including
checking file extensions and rejecting unsupported formats.
"""

import os
from typing import Tuple

# Supported file formats
SUPPORTED_FORMATS = {
    # Direct conversion formats (no extraction needed)
    "direct": [".pdf", ".epub"],
    # Archive formats (need extraction)
    "archive": [".zip", ".cbz", ".rar", ".cbr", ".7z", ".cb7"],
}

# Flattened list of all supported extensions
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_FORMATS["direct"] + SUPPORTED_FORMATS["archive"]


class UnsupportedFileFormatError(Exception):
    """Exception raised when an unsupported file format is encountered."""

    def __init__(self, filename: str, extension: str = None):
        self.filename = filename
        self.extension = extension

        if extension is None:
            message = (
                f"File '{filename}' has no extension. Please provide a file with a valid extension."
            )
        else:
            message = (
                f"File format '{extension}' is not supported. "
                f"Supported formats: {', '.join(ALL_SUPPORTED_EXTENSIONS)}"
            )

        super().__init__(message)
        self.message = message


def get_file_extension(filename: str) -> str:
    """
    Extract the file extension from a filename.

    Args:
        filename: The name of the file

    Returns:
        The lowercase file extension (including the dot), or empty string if none
    """
    if not filename:
        return ""

    _, ext = os.path.splitext(filename)
    return ext.lower()


def validate_file_extension(filename: str) -> Tuple[bool, str]:
    """
    Validate that a file has a supported extension.

    Args:
        filename: The name of the file to validate

    Returns:
        Tuple of (is_valid, extension)

    Raises:
        UnsupportedFileFormatError: If the file has no extension or an unsupported extension
    """
    if not filename:
        raise UnsupportedFileFormatError(filename or "unnamed file", None)

    extension = get_file_extension(filename)

    # Check for files without extension
    if not extension:
        raise UnsupportedFileFormatError(filename, None)

    # Check if extension is supported
    if extension not in ALL_SUPPORTED_EXTENSIONS:
        raise UnsupportedFileFormatError(filename, extension)

    return True, extension


def is_supported_format(filename: str) -> bool:
    """
    Check if a file has a supported format without raising an exception.

    Args:
        filename: The name of the file to check

    Returns:
        True if the file has a supported extension, False otherwise
    """
    try:
        validate_file_extension(filename)
        return True
    except UnsupportedFileFormatError:
        return False


def get_supported_formats_list() -> list:
    """
    Get a list of all supported file extensions.

    Returns:
        List of supported file extensions (e.g., ['.pdf', '.epub', '.zip', ...])
    """
    return ALL_SUPPORTED_EXTENSIONS.copy()


def get_supported_formats_string() -> str:
    """
    Get a human-readable string of supported file formats.

    Returns:
        Comma-separated string of supported extensions
    """
    return ", ".join(ALL_SUPPORTED_EXTENSIONS)
