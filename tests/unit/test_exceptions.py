# Copyright (c) 2025. All rights reserved.
"""Unit tests for custom exceptions module."""

import pytest

from src.exceptions import (
    AudioDeviceError,
    AudioFileCorruptedError,
    AudioFileError,
    AudioFileNotFoundError,
    AudioFileUnsupportedError,
    ConfigCorruptedError,
    ConfigInvalidFieldError,
    ConfigNotFoundError,
    ConfigurationError,
    DeviceDisconnectedError,
    DeviceNoOutputError,
    DeviceNotFoundError,
    ErrorCode,
    HotkeyConflictError,
    HotkeyError,
    HotkeyInvalidError,
    MUCError,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_codes_are_unique(self) -> None:
        """All error codes should be unique."""
        codes = [e.value for e in ErrorCode]
        assert len(codes) == len(set(codes))

    def test_config_codes_in_100_range(self) -> None:
        """Configuration error codes should be in 100 range."""
        assert ErrorCode.CONFIG_NOT_FOUND == 100
        assert ErrorCode.CONFIG_CORRUPTED == 101
        assert ErrorCode.CONFIG_INVALID_FIELD == 102
        assert ErrorCode.CONFIG_PERMISSION_DENIED == 103

    def test_device_codes_in_200_range(self) -> None:
        """Device error codes should be in 200 range."""
        assert ErrorCode.DEVICE_NOT_FOUND == 200
        assert ErrorCode.DEVICE_NO_OUTPUT == 201
        assert ErrorCode.DEVICE_DISCONNECTED == 202

    def test_file_codes_in_300_range(self) -> None:
        """File error codes should be in 300 range."""
        assert ErrorCode.FILE_NOT_FOUND == 300
        assert ErrorCode.FILE_CORRUPTED == 301
        assert ErrorCode.FILE_UNSUPPORTED_FORMAT == 302

    def test_hotkey_codes_in_400_range(self) -> None:
        """Hotkey error codes should be in 400 range."""
        assert ErrorCode.HOTKEY_INVALID == 400
        assert ErrorCode.HOTKEY_ALREADY_BOUND == 401


class TestMUCError:
    """Tests for base MUCError class."""

    def test_default_message(self) -> None:
        """MUCError should have default message."""
        error = MUCError()
        assert error.message == "An unexpected error occurred"

    def test_custom_message(self) -> None:
        """MUCError should accept custom message."""
        error = MUCError(message="Custom error message")
        assert error.message == "Custom error message"

    def test_default_suggestion(self) -> None:
        """MUCError should have default suggestion."""
        error = MUCError()
        assert error.suggestion == "Please try again or report this issue"

    def test_custom_suggestion(self) -> None:
        """MUCError should accept custom suggestion."""
        error = MUCError(suggestion="Try this instead")
        assert error.suggestion == "Try this instead"

    def test_details_dict(self) -> None:
        """MUCError should store details dict."""
        details = {"key": "value", "number": 42}
        error = MUCError(details=details)
        assert error.details == details

    def test_empty_details_by_default(self) -> None:
        """MUCError should have empty details by default."""
        error = MUCError()
        assert error.details == {}

    def test_str_includes_error_code(self) -> None:
        """String representation should include error code."""
        error = MUCError(message="Test error")
        assert "[E999]" in str(error)
        assert "Test error" in str(error)

    def test_format_for_user(self) -> None:
        """format_for_user should return user-friendly message."""
        error = MUCError(message="Something went wrong", suggestion="Do this instead")
        formatted = error.format_for_user()
        assert "Something went wrong" in formatted
        assert "Do this instead" in formatted
        assert "💡 Suggestion:" in formatted

    def test_is_exception(self) -> None:
        """MUCError should be an Exception."""
        error = MUCError()
        assert isinstance(error, Exception)

    def test_can_be_raised(self) -> None:
        """MUCError should be raisable.

        Raises:
            MUCError: Test exception to verify it can be raised.

        """
        with pytest.raises(MUCError) as exc_info:
            raise MUCError(message="Test")
        assert exc_info.value.message == "Test"


class TestConfigurationErrors:
    """Tests for configuration error classes."""

    def test_config_not_found_defaults(self) -> None:
        """ConfigNotFoundError should have correct defaults."""
        error = ConfigNotFoundError()
        assert error.code == ErrorCode.CONFIG_NOT_FOUND
        assert "not found" in error.message.lower()
        assert "setup" in error.suggestion.lower()

    def test_config_corrupted_defaults(self) -> None:
        """ConfigCorruptedError should have correct defaults."""
        error = ConfigCorruptedError()
        assert error.code == ErrorCode.CONFIG_CORRUPTED
        assert "corrupted" in error.message.lower()

    def test_config_invalid_field_defaults(self) -> None:
        """ConfigInvalidFieldError should have correct defaults."""
        error = ConfigInvalidFieldError()
        assert error.code == ErrorCode.CONFIG_INVALID_FIELD
        assert "invalid" in error.message.lower()

    def test_inheritance(self) -> None:
        """Configuration errors should inherit from ConfigurationError and MUCError."""
        error = ConfigNotFoundError()
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, MUCError)
        assert isinstance(error, Exception)


class TestAudioDeviceErrors:
    """Tests for audio device error classes."""

    def test_device_not_found_defaults(self) -> None:
        """DeviceNotFoundError should have correct defaults."""
        error = DeviceNotFoundError()
        assert error.code == ErrorCode.DEVICE_NOT_FOUND
        assert "not found" in error.message.lower()
        assert "devices" in error.suggestion.lower()

    def test_device_no_output_defaults(self) -> None:
        """DeviceNoOutputError should have correct defaults."""
        error = DeviceNoOutputError()
        assert error.code == ErrorCode.DEVICE_NO_OUTPUT
        assert "output" in error.message.lower()

    def test_device_disconnected_defaults(self) -> None:
        """DeviceDisconnectedError should have correct defaults."""
        error = DeviceDisconnectedError()
        assert error.code == ErrorCode.DEVICE_DISCONNECTED
        assert "disconnected" in error.message.lower()

    def test_inheritance(self) -> None:
        """Device errors should inherit from AudioDeviceError and MUCError."""
        error = DeviceNotFoundError()
        assert isinstance(error, AudioDeviceError)
        assert isinstance(error, MUCError)


class TestAudioFileErrors:
    """Tests for audio file error classes."""

    def test_file_not_found_defaults(self) -> None:
        """AudioFileNotFoundError should have correct defaults."""
        error = AudioFileNotFoundError()
        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert "not found" in error.message.lower()

    def test_file_corrupted_defaults(self) -> None:
        """AudioFileCorruptedError should have correct defaults."""
        error = AudioFileCorruptedError()
        assert error.code == ErrorCode.FILE_CORRUPTED
        assert "corrupted" in error.message.lower()

    def test_file_unsupported_defaults(self) -> None:
        """AudioFileUnsupportedError should have correct defaults."""
        error = AudioFileUnsupportedError()
        assert error.code == ErrorCode.FILE_UNSUPPORTED_FORMAT
        assert "unsupported" in error.message.lower()

    def test_inheritance(self) -> None:
        """File errors should inherit from AudioFileError and MUCError."""
        error = AudioFileCorruptedError()
        assert isinstance(error, AudioFileError)
        assert isinstance(error, MUCError)


class TestHotkeyErrors:
    """Tests for hotkey error classes."""

    def test_hotkey_invalid_defaults(self) -> None:
        """HotkeyInvalidError should have correct defaults."""
        error = HotkeyInvalidError()
        assert error.code == ErrorCode.HOTKEY_INVALID
        assert "invalid" in error.message.lower()

    def test_hotkey_conflict_defaults(self) -> None:
        """HotkeyConflictError should have correct defaults."""
        error = HotkeyConflictError()
        assert error.code == ErrorCode.HOTKEY_ALREADY_BOUND
        assert "assigned" in error.message.lower()

    def test_inheritance(self) -> None:
        """Hotkey errors should inherit from HotkeyError and MUCError."""
        error = HotkeyInvalidError()
        assert isinstance(error, HotkeyError)
        assert isinstance(error, MUCError)


class TestCustomMessages:
    """Tests for custom messages and details."""

    def test_device_error_with_details(self) -> None:
        """Device errors should preserve custom details."""
        error = DeviceNotFoundError(
            message="Device ID 5 not found",
            suggestion="Run muc devices to list available devices",
            details={"device_id": 5, "max_id": 10},
        )
        assert error.message == "Device ID 5 not found"
        assert "muc devices" in error.suggestion
        assert error.details["device_id"] == 5
        assert error.details["max_id"] == 10

    def test_file_error_with_path(self) -> None:
        """File errors should preserve path information."""
        error = AudioFileCorruptedError(
            message="Cannot read test.mp3",
            details={"path": "/sounds/test.mp3", "error": "Invalid frame header"},
        )
        assert "test.mp3" in error.message
        assert error.details["path"] == "/sounds/test.mp3"
