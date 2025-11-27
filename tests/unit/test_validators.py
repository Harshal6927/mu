# Copyright (c) 2025. All rights reserved.
"""Unit tests for validators module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import (
    AudioFileCorruptedError,
    AudioFileNotFoundError,
    AudioFileUnsupportedError,
    ConfigCorruptedError,
    ConfigInvalidFieldError,
    DeviceNoOutputError,
    DeviceNotFoundError,
)
from src.validators import (
    SUPPORTED_FORMATS,
    AudioFileInfo,
    DeviceInfo,
    validate_audio_file,
    validate_audio_file_safe,
    validate_config_data,
    validate_config_file,
    validate_device,
    validate_device_safe,
)


class TestSupportedFormats:
    """Tests for supported format constants."""

    def test_includes_common_formats(self) -> None:
        """Should include common audio formats."""
        assert ".wav" in SUPPORTED_FORMATS
        assert ".mp3" in SUPPORTED_FORMATS
        assert ".ogg" in SUPPORTED_FORMATS
        assert ".flac" in SUPPORTED_FORMATS
        assert ".m4a" in SUPPORTED_FORMATS

    def test_formats_are_lowercase(self) -> None:
        """All formats should be lowercase."""
        for fmt in SUPPORTED_FORMATS:
            assert fmt == fmt.lower()

    def test_formats_have_dots(self) -> None:
        """All formats should start with dots."""
        for fmt in SUPPORTED_FORMATS:
            assert fmt.startswith(".")


class TestValidateAudioFile:
    """Tests for validate_audio_file function."""

    def test_file_not_found(self, temp_dir: Path) -> None:
        """Should raise AudioFileNotFoundError for missing files."""
        missing_file = temp_dir / "nonexistent.wav"

        with pytest.raises(AudioFileNotFoundError) as exc_info:
            validate_audio_file(missing_file)

        assert "nonexistent.wav" in exc_info.value.message
        assert exc_info.value.details["path"] == str(missing_file)

    def test_unsupported_format(self, temp_dir: Path) -> None:
        """Should raise AudioFileUnsupportedError for unsupported formats."""
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.touch()

        with pytest.raises(AudioFileUnsupportedError) as exc_info:
            validate_audio_file(unsupported_file)

        assert ".xyz" in exc_info.value.message
        assert ".wav" in exc_info.value.suggestion  # Suggests valid formats

    def test_corrupted_file(self, temp_dir: Path) -> None:
        """Should raise AudioFileCorruptedError for unreadable files."""
        corrupted_file = temp_dir / "corrupted.wav"
        corrupted_file.write_bytes(b"not a valid wav file")

        with pytest.raises(AudioFileCorruptedError) as exc_info:
            validate_audio_file(corrupted_file)

        assert "corrupted.wav" in exc_info.value.message

    def test_valid_file_mock(self, temp_dir: Path) -> None:
        """Should return AudioFileInfo for valid files (mocked)."""
        valid_file = temp_dir / "test.wav"
        valid_file.touch()

        mock_info = MagicMock()
        mock_info.duration = 2.5
        mock_info.samplerate = 44100
        mock_info.channels = 2
        mock_info.format = "WAV"

        with patch("src.validators.sf.info", return_value=mock_info):
            result = validate_audio_file(valid_file)

        assert isinstance(result, AudioFileInfo)
        assert result.path == valid_file
        assert result.duration == 2.5
        assert result.sample_rate == 44100
        assert result.channels == 2
        assert result.is_valid is True


class TestValidateAudioFileSafe:
    """Tests for validate_audio_file_safe function."""

    def test_returns_invalid_for_missing_file(self, temp_dir: Path) -> None:
        """Should return invalid AudioFileInfo for missing files."""
        missing_file = temp_dir / "missing.wav"

        result = validate_audio_file_safe(missing_file)

        assert result.is_valid is False
        assert result.error is not None
        assert result.path == missing_file

    def test_returns_invalid_for_corrupted_file(self, temp_dir: Path) -> None:
        """Should return invalid AudioFileInfo for corrupted files."""
        corrupted_file = temp_dir / "bad.wav"
        corrupted_file.write_bytes(b"invalid")

        result = validate_audio_file_safe(corrupted_file)

        assert result.is_valid is False
        assert result.error is not None

    def test_returns_valid_for_good_file_mock(self, temp_dir: Path) -> None:
        """Should return valid AudioFileInfo for good files (mocked)."""
        valid_file = temp_dir / "good.wav"
        valid_file.touch()

        mock_info = MagicMock()
        mock_info.duration = 1.0
        mock_info.samplerate = 48000
        mock_info.channels = 1
        mock_info.format = "WAV"

        with patch("src.validators.sf.info", return_value=mock_info):
            result = validate_audio_file_safe(valid_file)

        assert result.is_valid is True
        assert result.error is None


class TestValidateDevice:
    """Tests for validate_device function."""

    def test_device_not_found_negative_id(self) -> None:
        """Should raise DeviceNotFoundError for negative device ID."""
        with patch("src.validators.sd.query_devices", return_value=[]), pytest.raises(DeviceNotFoundError):
            validate_device(-1)

    def test_device_not_found_high_id(self) -> None:
        """Should raise DeviceNotFoundError for ID higher than device count."""
        mock_devices = [
            {"name": "Device 1", "max_input_channels": 0, "max_output_channels": 2},
        ]

        with patch("src.validators.sd.query_devices", return_value=mock_devices):
            with pytest.raises(DeviceNotFoundError) as exc_info:
                validate_device(10)

            assert "10" in exc_info.value.message or "10" in str(exc_info.value.details)

    def test_device_no_output(self) -> None:
        """Should raise DeviceNoOutputError for input-only device."""
        mock_devices = [
            {"name": "Microphone", "max_input_channels": 2, "max_output_channels": 0},
        ]

        def query_mock(idx: int | None = None) -> list[dict[str, str | int]] | dict[str, str | int]:
            if idx is None:
                return mock_devices
            return mock_devices[idx]

        with patch("src.validators.sd.query_devices", side_effect=query_mock):
            with pytest.raises(DeviceNoOutputError) as exc_info:
                validate_device(0)

            assert "Microphone" in exc_info.value.message

    def test_valid_device(self) -> None:
        """Should return DeviceInfo for valid output device."""
        mock_devices = [
            {"name": "Speakers", "max_input_channels": 0, "max_output_channels": 2},
        ]

        def query_mock(idx: int | None = None) -> list[dict[str, str | int]] | dict[str, str | int]:
            if idx is None:
                return mock_devices
            return mock_devices[idx]

        with patch("src.validators.sd.query_devices", side_effect=query_mock):
            result = validate_device(0)

        assert isinstance(result, DeviceInfo)
        assert result.id == 0
        assert result.name == "Speakers"
        assert result.output_channels == 2
        assert result.is_valid_output is True


class TestValidateDeviceSafe:
    """Tests for validate_device_safe function."""

    def test_returns_none_for_invalid_device(self) -> None:
        """Should return None for invalid device."""
        with patch("src.validators.sd.query_devices", return_value=[]):
            result = validate_device_safe(99)
            assert result is None

    def test_returns_info_for_valid_device(self) -> None:
        """Should return DeviceInfo for valid device."""
        mock_devices = [
            {"name": "Headphones", "max_input_channels": 0, "max_output_channels": 2},
        ]

        def query_mock(idx: int | None = None) -> list[dict[str, str | int]] | dict[str, str | int]:
            if idx is None:
                return mock_devices
            return mock_devices[idx]

        with patch("src.validators.sd.query_devices", side_effect=query_mock):
            result = validate_device_safe(0)

        assert result is not None
        assert result.name == "Headphones"


class TestValidateConfigData:
    """Tests for validate_config_data function."""

    def test_valid_config(self) -> None:
        """Should return validated config for valid data."""
        data = {
            "output_device_id": 5,
            "volume": 0.75,
            "sounds_dir": "/path/to/sounds",
        }

        result = validate_config_data(data)

        assert result["output_device_id"] == 5
        assert result["volume"] == 0.75
        assert result["sounds_dir"] == "/path/to/sounds"

    def test_clamps_volume_above_1(self) -> None:
        """Should clamp volume above 1.0."""
        data = {"volume": 1.5}

        result = validate_config_data(data)

        assert result["volume"] == 1.0

    def test_clamps_volume_below_0(self) -> None:
        """Should clamp volume below 0.0."""
        data = {"volume": -0.5}

        result = validate_config_data(data)

        assert result["volume"] == 0.0

    def test_rejects_invalid_device_id(self) -> None:
        """Should reject non-integer device ID."""
        data = {"output_device_id": "five"}

        with pytest.raises(ConfigInvalidFieldError) as exc_info:
            validate_config_data(data)

        assert "output_device_id" in str(exc_info.value.details)

    def test_rejects_negative_device_id(self) -> None:
        """Should reject negative device ID."""
        data = {"output_device_id": -5}

        with pytest.raises(ConfigInvalidFieldError):
            validate_config_data(data)

    def test_rejects_invalid_volume_type(self) -> None:
        """Should reject non-numeric volume."""
        data = {"volume": "loud"}

        with pytest.raises(ConfigInvalidFieldError):
            validate_config_data(data)

    def test_rejects_invalid_sounds_dir_type(self) -> None:
        """Should reject non-string sounds_dir."""
        data = {"sounds_dir": 12345}

        with pytest.raises(ConfigInvalidFieldError):
            validate_config_data(data)

    def test_allows_none_device_id(self) -> None:
        """Should allow None for device ID."""
        data = {"output_device_id": None}

        result = validate_config_data(data)

        assert "output_device_id" not in result  # None values not included

    def test_default_volume(self) -> None:
        """Should use default volume when not specified."""
        data = {}

        result = validate_config_data(data)

        assert result["volume"] == 1.0


class TestValidateConfigFile:
    """Tests for validate_config_file function."""

    def test_missing_file_returns_empty(self) -> None:
        """Should return empty dict for missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing.json"

            result = validate_config_file(missing_file)

            assert result == {}

    def test_corrupted_json(self) -> None:
        """Should raise ConfigCorruptedError for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text("{ invalid json }", encoding="utf-8")

            with pytest.raises(ConfigCorruptedError):
                validate_config_file(config_file)

    def test_valid_file(self) -> None:
        """Should return validated data for valid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            data = {"output_device_id": 3, "volume": 0.5}
            config_file.write_text(json.dumps(data), encoding="utf-8")

            result = validate_config_file(config_file)

            assert result["output_device_id"] == 3
            assert result["volume"] == 0.5

    def test_empty_file_is_corrupted(self) -> None:
        """Should treat empty file as corrupted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text("", encoding="utf-8")

            with pytest.raises(ConfigCorruptedError):
                validate_config_file(config_file)
