# Copyright (c) 2025. All rights reserved.
# ruff: noqa: DOC201, DOC402
"""Unit tests for the hotkey manager module."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.hotkey_manager import HotkeyManager


@pytest.fixture
def temp_config_dir() -> Generator[Path]:
    """Create a temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".muc"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield config_dir


@pytest.fixture
def mock_profile_manager(temp_config_dir: Path) -> MagicMock:
    """Create a mock ProfileManager instance."""
    mock_profile = MagicMock()
    mock_profile.hotkeys = {}
    mock_profile.hotkey_mode = "merged"

    mock_pm = MagicMock()
    mock_pm.get_active_profile.return_value = mock_profile
    return mock_pm


@pytest.fixture
def hotkey_manager(mock_profile_manager: MagicMock) -> HotkeyManager:
    """Create a HotkeyManager with a mock profile manager."""
    return HotkeyManager(profile_manager=mock_profile_manager)


class TestHotkeyNormalization:
    """Tests for hotkey string normalization."""

    def test_normalize_simple_function_key(self, hotkey_manager: HotkeyManager) -> None:
        """Test normalizing simple function key aliases."""
        assert hotkey_manager.normalize_hotkey("f1") == "<f1>"
        assert hotkey_manager.normalize_hotkey("f12") == "<f12>"
        assert hotkey_manager.normalize_hotkey("F5") == "<f5>"

    def test_normalize_already_formatted(self, hotkey_manager: HotkeyManager) -> None:
        """Test already formatted hotkeys pass through."""
        assert hotkey_manager.normalize_hotkey("<f1>") == "<f1>"
        assert hotkey_manager.normalize_hotkey("<ctrl>") == "<ctrl>"

    def test_normalize_modifier_plus_key(self, hotkey_manager: HotkeyManager) -> None:
        """Test normalizing modifier+key combinations."""
        assert hotkey_manager.normalize_hotkey("ctrl+a") == "<ctrl>+a"
        assert hotkey_manager.normalize_hotkey("alt+1") == "<alt>+1"
        assert hotkey_manager.normalize_hotkey("shift+f1") == "<shift>+<f1>"

    def test_normalize_multiple_modifiers(self, hotkey_manager: HotkeyManager) -> None:
        """Test normalizing multiple modifiers."""
        result = hotkey_manager.normalize_hotkey("ctrl+shift+a")
        assert result == "<ctrl>+<shift>+a"

    def test_normalize_with_angle_brackets(self, hotkey_manager: HotkeyManager) -> None:
        """Test normalizing hotkeys with angle brackets."""
        result = hotkey_manager.normalize_hotkey("<ctrl>+<shift>+1")
        assert result == "<ctrl>+<shift>+1"

    def test_normalize_special_keys(self, hotkey_manager: HotkeyManager) -> None:
        """Test normalizing special key aliases."""
        assert hotkey_manager.normalize_hotkey("space") == "<space>"
        assert hotkey_manager.normalize_hotkey("enter") == "<enter>"
        assert hotkey_manager.normalize_hotkey("esc") == "<esc>"

    def test_normalize_invalid_returns_special_format(self, hotkey_manager: HotkeyManager) -> None:
        """Test normalizing unknown keys wraps in angle brackets."""
        result = hotkey_manager.normalize_hotkey("unknownkey")
        assert result == "<unknownkey>"

    def test_normalize_empty_returns_none(self, hotkey_manager: HotkeyManager) -> None:
        """Test empty hotkey returns None."""
        assert hotkey_manager.normalize_hotkey("") is None
        assert hotkey_manager.normalize_hotkey("   ") is None


class TestHotkeyBinding:
    """Tests for hotkey binding operations."""

    def test_bind_hotkey(self, hotkey_manager: HotkeyManager, mock_profile_manager: MagicMock) -> None:
        """Test binding a hotkey to a sound."""
        result = hotkey_manager.bind("f1", "airhorn")
        assert result is True
        assert hotkey_manager.bindings["<f1>"] == "airhorn"
        mock_profile_manager.save_profile.assert_called()

    def test_bind_normalizes_hotkey(
        self,
        hotkey_manager: HotkeyManager,
        mock_profile_manager: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test binding normalizes the hotkey string."""
        hotkey_manager.bind("ctrl+a", "applause")
        assert "<ctrl>+a" in hotkey_manager.bindings

    def test_unbind_hotkey(
        self,
        hotkey_manager: HotkeyManager,
        mock_profile_manager: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test unbinding a hotkey."""
        hotkey_manager.bind("f1", "airhorn")
        result = hotkey_manager.unbind("f1")
        assert result is True
        assert "<f1>" not in hotkey_manager.bindings

    def test_unbind_nonexistent_returns_false(self, hotkey_manager: HotkeyManager) -> None:
        """Test unbinding nonexistent hotkey returns False."""
        result = hotkey_manager.unbind("f1")
        assert result is False

    def test_unbind_sound(
        self,
        hotkey_manager: HotkeyManager,
        mock_profile_manager: MagicMock,  # noqa: ARG002
    ) -> None:
        """Test unbinding all hotkeys for a sound."""
        hotkey_manager.bind("f1", "airhorn")
        hotkey_manager.bind("f2", "airhorn")
        hotkey_manager.bind("f3", "other")

        count = hotkey_manager.unbind_sound("airhorn")
        assert count == 2
        assert "<f1>" not in hotkey_manager.bindings
        assert "<f2>" not in hotkey_manager.bindings
        assert "<f3>" in hotkey_manager.bindings

    def test_get_binding(self, hotkey_manager: HotkeyManager) -> None:
        """Test getting binding for a hotkey."""
        hotkey_manager.bind("f1", "airhorn")
        assert hotkey_manager.get_binding("f1") == "airhorn"
        assert hotkey_manager.get_binding("f2") is None

    def test_get_all_bindings(self, hotkey_manager: HotkeyManager) -> None:
        """Test getting all bindings."""
        hotkey_manager.bind("f1", "airhorn")
        hotkey_manager.bind("f2", "rickroll")

        bindings = hotkey_manager.get_all_bindings()
        assert len(bindings) == 2
        assert bindings["<f1>"] == "airhorn"
        assert bindings["<f2>"] == "rickroll"

    def test_clear_all(self, hotkey_manager: HotkeyManager, mock_profile_manager: MagicMock) -> None:
        """Test clearing all bindings."""
        hotkey_manager.bind("f1", "airhorn")
        hotkey_manager.bind("f2", "rickroll")

        count = hotkey_manager.clear_all()
        assert count == 2
        assert hotkey_manager.bindings == {}
        mock_profile_manager.save_profile.assert_called()

    def test_get_hotkeys_for_sound(self, hotkey_manager: HotkeyManager) -> None:
        """Test getting all hotkeys bound to a sound."""
        hotkey_manager.bind("f1", "airhorn")
        hotkey_manager.bind("ctrl+a", "airhorn")
        hotkey_manager.bind("f2", "other")

        hotkeys = hotkey_manager.get_hotkeys_for_sound("airhorn")
        assert len(hotkeys) == 2
        assert "<f1>" in hotkeys
        assert "<ctrl>+a" in hotkeys

    def test_is_valid_hotkey(self, hotkey_manager: HotkeyManager) -> None:
        """Test validating hotkey strings."""
        assert hotkey_manager.is_valid_hotkey("f1") is True
        assert hotkey_manager.is_valid_hotkey("ctrl+a") is True
        assert hotkey_manager.is_valid_hotkey("") is False


class TestHotkeyManagerPersistence:
    """Tests for hotkey persistence."""

    def test_load_bindings_from_profile(self) -> None:
        """Test loading bindings from profile on init."""
        mock_profile = MagicMock()
        mock_profile.hotkeys = {"<f1>": "airhorn", "<f2>": "rickroll"}

        mock_pm = MagicMock()
        mock_pm.get_active_profile.return_value = mock_profile

        manager = HotkeyManager(profile_manager=mock_pm)

        assert manager.bindings == {"<f1>": "airhorn", "<f2>": "rickroll"}

    def test_save_bindings_to_profile(
        self,
        hotkey_manager: HotkeyManager,
        mock_profile_manager: MagicMock,
    ) -> None:
        """Test bindings are saved to profile."""
        mock_profile = mock_profile_manager.get_active_profile.return_value
        hotkey_manager.bind("f1", "airhorn")

        # Check that profile.hotkeys was updated
        assert mock_profile.hotkeys == {"<f1>": "airhorn"}
        mock_profile_manager.save_profile.assert_called()
