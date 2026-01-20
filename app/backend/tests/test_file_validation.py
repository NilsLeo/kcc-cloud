"""Tests for file validation functionality."""

import pytest
from utils.routes import allowed_file


class TestFileValidation:
    """Test file validation functions."""

    def test_allowed_file_extensions(self):
        """Test that allowed file extensions are accepted."""
        # Comic formats
        assert allowed_file("test.cbz") is True
        assert allowed_file("test.cbr") is True
        assert allowed_file("test.cb7") is True
        assert allowed_file("test.cbt") is True

        # Document formats
        assert allowed_file("test.pdf") is True
        assert allowed_file("test.epub") is True

        # Archive formats
        assert allowed_file("test.zip") is True
        assert allowed_file("test.rar") is True
        assert allowed_file("test.7z") is True
        assert allowed_file("test.tar") is True

        # Image formats
        assert allowed_file("test.jpg") is True
        assert allowed_file("test.jpeg") is True
        assert allowed_file("test.png") is True
        assert allowed_file("test.gif") is True
        assert allowed_file("test.bmp") is True
        assert allowed_file("test.webp") is True

    def test_disallowed_file_extensions(self):
        """Test that disallowed file extensions are rejected."""
        assert allowed_file("test.exe") is False
        assert allowed_file("test.sh") is False
        assert allowed_file("test.bat") is False
        assert allowed_file("test.dll") is False
        assert allowed_file("test.txt") is False
        assert allowed_file("test.doc") is False

    def test_case_insensitive_extensions(self):
        """Test that file extension checking is case-insensitive."""
        assert allowed_file("test.CBZ") is True
        assert allowed_file("test.Cbz") is True
        assert allowed_file("test.PDF") is True
        assert allowed_file("test.JPEG") is True

    def test_no_extension(self):
        """Test that files without extensions are rejected."""
        assert allowed_file("test") is False
        assert allowed_file("") is False

    def test_multiple_dots_in_filename(self):
        """Test files with multiple dots in filename."""
        assert allowed_file("my.comic.book.cbz") is True
        assert allowed_file("test.backup.exe") is False
