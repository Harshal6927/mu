# Copyright (c) 2025. All rights reserved.
"""Validation utilities for MUC Soundboard."""

import json
from pathlib import Path
from typing import NamedTuple

import sounddevice as sd
import soundfile as sf

from .exceptions import (
    AudioFileCorruptedError,
    AudioFileNotFoundError,
    AudioFileTooLargeError,
    AudioFileUnsupportedError,
    ConfigCorruptedError,
    ConfigInvalidFieldError,
    DeviceNoOutputError,
    DeviceNotFoundError,
)
from .logging_config import get_logger

logger = get_logger(__name__)

SUPPORTED_FORMATS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}

# Maximum recommended audio duration in seconds (5 minutes)
MAX_AUDIO_DURATION = 300


class AudioFileInfo(NamedTuple):
    """Information about an audio file."""

    path: Path
    duration: float  # seconds
    sample_rate: int
    channels: int
    format: str
    is_valid: bool
    error: str | None = None


class DeviceInfo(NamedTuple):
    """Information about an audio device."""

    id: int
    name: str
    input_channels: int
    output_channels: int
    is_valid_output: bool


def validate_audio_file(file_path: Path, *, warn_long_duration: bool = True) -> AudioFileInfo:
    """Validate an audio file and return its information.

    Args:
        file_path: Path to the audio file
        warn_long_duration: If True, warn about files longer than 5 minutes

    Returns:
        AudioFileInfo with file details and validation status

    """

    def _check_duration(duration: float, file_path: Path) -> None:
        """Check if audio duration exceeds maximum and raise if needed."""
        if duration > MAX_AUDIO_DURATION:
            logger.warning(f"Audio file is long ({duration:.1f}s): {file_path.name}")
            raise AudioFileTooLargeError(
                f"Audio file is {duration / 60:.1f} minutes long",
                suggestion="Consider using shorter audio clips for soundboard use",
                details={"path": str(file_path), "duration": duration},
            )

    logger.debug(f"Validating audio file: {file_path}")

    if not file_path.exists():
        logger.warning(f"Audio file not found: {file_path}")
        raise AudioFileNotFoundError(
            f"File not found: {file_path.name}",
            details={"path": str(file_path)},
        )

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        logger.warning(f"Unsupported format: {suffix}")
        raise AudioFileUnsupportedError(
            f"Unsupported format: {suffix}",
            suggestion=f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}",
            details={"path": str(file_path), "format": suffix},
        )

    try:
        info = sf.info(str(file_path))
        duration = info.duration
        sample_rate = info.samplerate
        channels = info.channels
        file_format = info.format

        logger.debug(
            f"Audio file valid: {file_path.name} (duration={duration:.2f}s, rate={sample_rate}, channels={channels})",
        )

        # Warn about long audio files
        if warn_long_duration:
            _check_duration(duration, file_path)

        return AudioFileInfo(
            path=file_path,
            duration=duration,
            sample_rate=sample_rate,
            channels=channels,
            format=file_format,
            is_valid=True,
        )

    except (AudioFileNotFoundError, AudioFileUnsupportedError, AudioFileTooLargeError):
        raise
    except (OSError, RuntimeError) as e:
        logger.exception(f"Failed to read audio file {file_path}")
        raise AudioFileCorruptedError(
            f"Cannot read audio file: {file_path.name}",
            suggestion="The file may be corrupted. Try re-downloading or re-encoding it.",
            details={"path": str(file_path), "error": str(e)},
        ) from e


def validate_audio_file_safe(file_path: Path, *, warn_long_duration: bool = False) -> AudioFileInfo:
    """Validate audio file without raising exceptions.

    Returns AudioFileInfo with is_valid=False and error message if invalid.

    Args:
        file_path: Path to the audio file
        warn_long_duration: If True, treat long files as invalid

    Returns:
        AudioFileInfo with validation status

    """
    try:
        return validate_audio_file(file_path, warn_long_duration=warn_long_duration)
    except (AudioFileNotFoundError, AudioFileUnsupportedError, AudioFileCorruptedError, AudioFileTooLargeError) as e:
        return AudioFileInfo(
            path=file_path,
            duration=0,
            sample_rate=0,
            channels=0,
            format="unknown",
            is_valid=False,
            error=str(e),
        )


def validate_device(device_id: int) -> DeviceInfo:
    """Validate an audio device.

    Args:
        device_id: ID of the device to validate

    Returns:
        DeviceInfo with device details

    """
    logger.debug(f"Validating device ID: {device_id}")

    devices = sd.query_devices()
    if device_id < 0 or device_id >= len(devices):
        raise DeviceNotFoundError(
            f"Device ID {device_id} does not exist",
            suggestion="Run 'muc devices' to see available device IDs",
            details={"device_id": device_id, "max_id": len(devices) - 1},
        )

    device = sd.query_devices(device_id)
    # Type narrowing: when called with int, returns dict not DeviceList
    device_dict: dict = device  # type: ignore[assignment]
    name = str(device_dict["name"])
    input_channels = int(device_dict["max_input_channels"])
    output_channels = int(device_dict["max_output_channels"])

    if output_channels == 0:
        raise DeviceNoOutputError(
            f"Device '{name}' has no output channels",
            suggestion="Select a device with output capability, like speakers or CABLE Input",
            details={"device_id": device_id, "name": name},
        )

    logger.debug(f"Device valid: {name} (outputs={output_channels})")

    return DeviceInfo(
        id=device_id,
        name=name,
        input_channels=input_channels,
        output_channels=output_channels,
        is_valid_output=True,
    )


def validate_device_safe(device_id: int) -> DeviceInfo | None:
    """Validate device without raising exceptions.

    Args:
        device_id: ID of the device to validate

    Returns:
        DeviceInfo if valid, None if invalid

    """
    try:
        return validate_device(device_id)
    except (DeviceNotFoundError, DeviceNoOutputError):
        return None


def validate_config_data(data: dict) -> dict:
    """Validate configuration data and return sanitized version.

    Args:
        data: Raw configuration dictionary

    Returns:
        Validated and sanitized configuration

    """
    logger.debug("Validating configuration data")

    validated = {}
    errors = []

    # Validate output_device_id
    device_id = data.get("output_device_id")
    if device_id is not None:
        if not isinstance(device_id, int) or device_id < 0:
            errors.append(f"output_device_id must be a non-negative integer, got: {device_id}")
        else:
            validated["output_device_id"] = device_id

    # Validate volume
    volume = data.get("volume", 1.0)
    if not isinstance(volume, int | float):
        errors.append(f"volume must be a number, got: {type(volume).__name__}")
    elif not 0.0 <= volume <= 1.0:
        logger.warning(f"Volume {volume} out of range, clamping to [0.0, 1.0]")
        validated["volume"] = max(0.0, min(1.0, float(volume)))
    else:
        validated["volume"] = float(volume)

    # Validate sounds_dir
    sounds_dir = data.get("sounds_dir")
    if sounds_dir is not None:
        if not isinstance(sounds_dir, str):
            errors.append(f"sounds_dir must be a string, got: {type(sounds_dir).__name__}")
        else:
            validated["sounds_dir"] = sounds_dir

    # Validate hotkeys
    hotkeys = data.get("hotkeys", {})
    if not isinstance(hotkeys, dict):
        errors.append(f"hotkeys must be a dictionary, got: {type(hotkeys).__name__}")
    else:
        validated["hotkeys"] = hotkeys

    # Validate hotkey_mode
    hotkey_mode = data.get("hotkey_mode", "merged")
    valid_modes = {"default", "custom", "merged"}
    if hotkey_mode not in valid_modes:
        logger.warning(f"Invalid hotkey_mode '{hotkey_mode}', using 'merged'")
        validated["hotkey_mode"] = "merged"
    else:
        validated["hotkey_mode"] = hotkey_mode

    if errors:
        raise ConfigInvalidFieldError(
            "Invalid configuration values",
            suggestion="Check your config file at ~/.muc/config.json",
            details={"errors": errors},
        )

    logger.debug("Configuration validation passed")
    return validated


def validate_config_file(config_path: Path) -> dict:
    """Load and validate a configuration file.

    Args:
        config_path: Path to the config file

    Returns:
        Validated configuration dictionary

    """
    logger.debug(f"Loading config from: {config_path}")

    if not config_path.exists():
        logger.info("Config file not found, using defaults")
        return {}

    try:
        with config_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.exception("Config file corrupted")
        raise ConfigCorruptedError(
            "Configuration file contains invalid JSON",
            suggestion="Delete the file and run 'muc setup' to recreate it",
            details={"path": str(config_path), "error": str(e)},
        ) from e
    except OSError as e:
        logger.exception("Cannot read config file")
        raise ConfigCorruptedError(
            f"Cannot read configuration file: {e}",
            details={"path": str(config_path)},
        ) from e

    return validate_config_data(data)
