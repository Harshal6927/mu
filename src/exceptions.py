# Copyright (c) 2025. All rights reserved.
"""Custom exceptions for MUC Soundboard."""

from enum import IntEnum
from typing import ClassVar


class ErrorCode(IntEnum):
    """Error codes for MUC exceptions."""

    # Configuration errors (1xx)
    CONFIG_NOT_FOUND = 100
    CONFIG_CORRUPTED = 101
    CONFIG_INVALID_FIELD = 102
    CONFIG_PERMISSION_DENIED = 103

    # Audio device errors (2xx)
    DEVICE_NOT_FOUND = 200
    DEVICE_NO_OUTPUT = 201
    DEVICE_DISCONNECTED = 202
    DEVICE_BUSY = 203
    DEVICE_PERMISSION_DENIED = 204

    # Audio file errors (3xx)
    FILE_NOT_FOUND = 300
    FILE_CORRUPTED = 301
    FILE_UNSUPPORTED_FORMAT = 302
    FILE_PERMISSION_DENIED = 303
    FILE_TOO_LARGE = 304

    # Hotkey errors (4xx)
    HOTKEY_INVALID = 400
    HOTKEY_ALREADY_BOUND = 401
    HOTKEY_SYSTEM_RESERVED = 402

    # General errors (9xx)
    UNKNOWN_ERROR = 999


class MUCError(Exception):
    """Base exception for all MUC errors.

    Attributes:
        code: Numeric error code for programmatic handling
        message: Human-readable error message
        suggestion: Recovery suggestion for the user
        details: Additional context (for logging)

    """

    code: ClassVar[ErrorCode] = ErrorCode.UNKNOWN_ERROR
    default_message: ClassVar[str] = "An unexpected error occurred"
    default_suggestion: ClassVar[str] = "Please try again or report this issue"

    def __init__(
        self,
        message: str | None = None,
        suggestion: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Initialize a MUC error.

        Args:
            message: Human-readable error message
            suggestion: Recovery suggestion for the user
            details: Additional context (for logging)

        """
        self.message = message or self.default_message
        self.suggestion = suggestion or self.default_suggestion
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation with error code.

        Returns:
            String representation with error code and message.

        """
        return f"[E{self.code}] {self.message}"

    def format_for_user(self) -> str:
        """Format error message for end-user display.

        Returns:
            Formatted error message with suggestion for end-user display.

        """
        return f"{self.message}\n💡 Suggestion: {self.suggestion}"


# Configuration Errors
class ConfigurationError(MUCError):
    """Base class for configuration-related errors."""

    code: ClassVar[ErrorCode] = ErrorCode.CONFIG_CORRUPTED
    default_message: ClassVar[str] = "Configuration error"


class ConfigNotFoundError(ConfigurationError):
    """Config file does not exist."""

    code: ClassVar[ErrorCode] = ErrorCode.CONFIG_NOT_FOUND
    default_message: ClassVar[str] = "Configuration file not found"
    default_suggestion: ClassVar[str] = "Run 'muc setup' to create a new configuration"


class ConfigCorruptedError(ConfigurationError):
    """Config file is corrupted or invalid JSON."""

    code: ClassVar[ErrorCode] = ErrorCode.CONFIG_CORRUPTED
    default_message: ClassVar[str] = "Configuration file is corrupted"
    default_suggestion: ClassVar[str] = "Delete ~/.muc/config.json and run 'muc setup' again"


class ConfigInvalidFieldError(ConfigurationError):
    """Config contains invalid field values."""

    code: ClassVar[ErrorCode] = ErrorCode.CONFIG_INVALID_FIELD
    default_message: ClassVar[str] = "Invalid configuration value"
    default_suggestion: ClassVar[str] = "Check your configuration file for invalid values"


class ConfigPermissionError(ConfigurationError):
    """Config file permission denied."""

    code: ClassVar[ErrorCode] = ErrorCode.CONFIG_PERMISSION_DENIED
    default_message: ClassVar[str] = "Permission denied accessing configuration"
    default_suggestion: ClassVar[str] = "Check file permissions for ~/.muc/"


# Audio Device Errors
class AudioDeviceError(MUCError):
    """Base class for audio device errors."""

    code: ClassVar[ErrorCode] = ErrorCode.DEVICE_NOT_FOUND
    default_message: ClassVar[str] = "Audio device error"


class DeviceNotFoundError(AudioDeviceError):
    """Specified device ID does not exist."""

    code: ClassVar[ErrorCode] = ErrorCode.DEVICE_NOT_FOUND
    default_message: ClassVar[str] = "Audio device not found"
    default_suggestion: ClassVar[str] = "Run 'muc devices' to see available devices, then 'muc setup' to reconfigure"


class DeviceNoOutputError(AudioDeviceError):
    """Device has no output channels."""

    code: ClassVar[ErrorCode] = ErrorCode.DEVICE_NO_OUTPUT
    default_message: ClassVar[str] = "Selected device has no output channels"
    default_suggestion: ClassVar[str] = "Select a device with output capability (speakers or virtual cable)"


class DeviceDisconnectedError(AudioDeviceError):
    """Device was disconnected during operation."""

    code: ClassVar[ErrorCode] = ErrorCode.DEVICE_DISCONNECTED
    default_message: ClassVar[str] = "Audio device was disconnected"
    default_suggestion: ClassVar[str] = (
        "Reconnect the device and try again, or run 'muc setup' to select a different device"
    )


class DeviceBusyError(AudioDeviceError):
    """Device is busy or in use by another application."""

    code: ClassVar[ErrorCode] = ErrorCode.DEVICE_BUSY
    default_message: ClassVar[str] = "Audio device is busy"
    default_suggestion: ClassVar[str] = "Close other applications using the device and try again"


class DevicePermissionError(AudioDeviceError):
    """Permission denied accessing device."""

    code: ClassVar[ErrorCode] = ErrorCode.DEVICE_PERMISSION_DENIED
    default_message: ClassVar[str] = "Permission denied accessing audio device"
    default_suggestion: ClassVar[str] = "Check your system's audio permissions"


# Audio File Errors
class AudioFileError(MUCError):
    """Base class for audio file errors."""

    code: ClassVar[ErrorCode] = ErrorCode.FILE_NOT_FOUND
    default_message: ClassVar[str] = "Audio file error"


class AudioFileNotFoundError(AudioFileError):
    """Audio file does not exist."""

    code: ClassVar[ErrorCode] = ErrorCode.FILE_NOT_FOUND
    default_message: ClassVar[str] = "Audio file not found"
    default_suggestion: ClassVar[str] = "Check the sounds directory and ensure the file exists"


class AudioFileCorruptedError(AudioFileError):
    """Audio file is corrupted or unreadable."""

    code: ClassVar[ErrorCode] = ErrorCode.FILE_CORRUPTED
    default_message: ClassVar[str] = "Audio file is corrupted or unreadable"
    default_suggestion: ClassVar[str] = "Try re-downloading or re-encoding the audio file"


class AudioFileUnsupportedError(AudioFileError):
    """Audio file format is not supported."""

    code: ClassVar[ErrorCode] = ErrorCode.FILE_UNSUPPORTED_FORMAT
    default_message: ClassVar[str] = "Unsupported audio format"
    default_suggestion: ClassVar[str] = "Convert the file to WAV, MP3, OGG, FLAC, or M4A format"


class AudioFilePermissionError(AudioFileError):
    """Permission denied accessing audio file."""

    code: ClassVar[ErrorCode] = ErrorCode.FILE_PERMISSION_DENIED
    default_message: ClassVar[str] = "Permission denied accessing audio file"
    default_suggestion: ClassVar[str] = "Check file permissions for the audio file"


class AudioFileTooLargeError(AudioFileError):
    """Audio file is too large."""

    code: ClassVar[ErrorCode] = ErrorCode.FILE_TOO_LARGE
    default_message: ClassVar[str] = "Audio file is too large"
    default_suggestion: ClassVar[str] = "Consider using a shorter audio clip (under 5 minutes recommended)"


# Hotkey Errors
class HotkeyError(MUCError):
    """Base class for hotkey errors."""

    code: ClassVar[ErrorCode] = ErrorCode.HOTKEY_INVALID
    default_message: ClassVar[str] = "Hotkey error"


class HotkeyInvalidError(HotkeyError):
    """Invalid hotkey specification."""

    code: ClassVar[ErrorCode] = ErrorCode.HOTKEY_INVALID
    default_message: ClassVar[str] = "Invalid hotkey format"
    default_suggestion: ClassVar[str] = "Use format like '<f1>', '<ctrl>+<alt>+a', or '<shift>+1'"


class HotkeyConflictError(HotkeyError):
    """Hotkey is already bound."""

    code: ClassVar[ErrorCode] = ErrorCode.HOTKEY_ALREADY_BOUND
    default_message: ClassVar[str] = "Hotkey is already assigned"
    default_suggestion: ClassVar[str] = "Choose a different hotkey or unbind the existing one first"


class HotkeySystemReservedError(HotkeyError):
    """Hotkey is reserved by the system."""

    code: ClassVar[ErrorCode] = ErrorCode.HOTKEY_SYSTEM_RESERVED
    default_message: ClassVar[str] = "Hotkey is reserved by the system"
    default_suggestion: ClassVar[str] = "Choose a different hotkey that is not used by Windows"
