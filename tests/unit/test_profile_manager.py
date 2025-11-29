# Copyright (c) 2025. All rights reserved.
"""Tests for profile manager module."""

import json
import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest

from src.profile_manager import Profile, ProfileManager


class TestProfile:
    """Test the Profile dataclass."""

    def test_profile_creation_basic(self) -> None:
        """Test basic profile creation."""
        profile = Profile(name="test")
        assert profile.name == "test"
        assert profile.display_name == "Test"
        assert not profile.description
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.updated_at, datetime)

    def test_profile_creation_with_display_name(self) -> None:
        """Test profile creation with custom display name."""
        profile = Profile(name="my_profile", display_name="My Custom Profile")
        assert profile.name == "my_profile"
        assert profile.display_name == "My Custom Profile"

    def test_profile_display_name_auto_generated(self) -> None:
        """Test that display name is auto-generated from name."""
        profile = Profile(name="csgo_competitive")
        assert profile.display_name == "Csgo Competitive"

    def test_profile_settings_properties(self) -> None:
        """Test profile settings properties."""
        profile = Profile(
            name="test",
            settings={
                "output_device_id": 5,
                "volume": 0.8,
                "sounds_dir": "/path/to/sounds",
                "hotkeys": {"<f1>": "sound1"},
                "hotkey_mode": "custom",
            },
        )
        assert profile.output_device_id == 5
        assert profile.volume == 0.8
        assert profile.sounds_dir == "/path/to/sounds"
        assert profile.hotkeys == {"<f1>": "sound1"}
        assert profile.hotkey_mode == "custom"

    def test_profile_settings_setters(self) -> None:
        """Test profile settings setters."""
        profile = Profile(name="test")
        profile.output_device_id = 10
        profile.volume = 0.5
        profile.sounds_dir = "/new/path"
        profile.hotkeys = {"<f2>": "sound2"}
        profile.hotkey_mode = "merged"

        assert profile.output_device_id == 10
        assert profile.volume == 0.5
        assert profile.sounds_dir == "/new/path"
        assert profile.hotkeys == {"<f2>": "sound2"}
        assert profile.hotkey_mode == "merged"

    def test_profile_sounds_dirs(self) -> None:
        """Test multiple sounds directories."""
        profile = Profile(
            name="test",
            settings={"sounds_dirs": ["/path/one", "/path/two"]},
        )
        assert profile.sounds_dirs == ["/path/one", "/path/two"]

    def test_profile_sounds_dirs_fallback_to_sounds_dir(self) -> None:
        """Test sounds_dirs falls back to sounds_dir if not set."""
        profile = Profile(
            name="test",
            settings={"sounds_dir": "/path/single"},
        )
        assert profile.sounds_dirs == ["/path/single"]

    def test_profile_to_dict(self) -> None:
        """Test profile serialization to dict."""
        profile = Profile(
            name="test",
            display_name="Test Profile",
            description="A test profile",
            settings={"volume": 0.7},
        )
        data = profile.to_dict()

        assert data["name"] == "test"
        assert data["display_name"] == "Test Profile"
        assert data["description"] == "A test profile"
        assert data["settings"]["volume"] == 0.7
        assert "created_at" in data
        assert "updated_at" in data

    def test_profile_from_dict(self) -> None:
        """Test profile deserialization from dict."""
        data = {
            "name": "test",
            "display_name": "Test Profile",
            "description": "A test",
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-02T12:00:00",
            "settings": {"volume": 0.6},
        }
        profile = Profile.from_dict(data)

        assert profile.name == "test"
        assert profile.display_name == "Test Profile"
        assert profile.description == "A test"
        assert profile.volume == 0.6


class TestProfileManager:
    """Test the ProfileManager class."""

    @pytest.fixture
    def temp_base_dir(self) -> Generator[Path]:
        """Create a temporary base directory for testing.

        Yields:
            Path: Temporary directory path.

        """
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_base_dir: Path) -> ProfileManager:
        """Create a ProfileManager with a temp directory.

        Returns:
            ProfileManager: Manager instance using temp directory.

        """
        return ProfileManager(base_dir=temp_base_dir)

    def test_initialization_creates_directories(self, temp_base_dir: Path) -> None:
        """Test that initialization creates necessary directories."""
        ProfileManager(base_dir=temp_base_dir)
        assert (temp_base_dir / "profiles").exists()

    def test_initialization_creates_default_profile(self, manager: ProfileManager) -> None:
        """Test that initialization creates a default profile."""
        profiles = manager.list_profiles()
        assert "default" in profiles

    def test_list_profiles(self, manager: ProfileManager) -> None:
        """Test listing profiles."""
        manager.create_profile("profile1")
        manager.create_profile("profile2")

        profiles = manager.list_profiles()
        assert "default" in profiles
        assert "profile1" in profiles
        assert "profile2" in profiles

    def test_get_profile(self, manager: ProfileManager) -> None:
        """Test getting a profile by name."""
        profile = manager.get_profile("default")
        assert profile is not None
        assert profile.name == "default"

    def test_get_profile_not_found(self, manager: ProfileManager) -> None:
        """Test getting a non-existent profile returns None."""
        profile = manager.get_profile("nonexistent")
        assert profile is None

    def test_get_active_profile(self, manager: ProfileManager) -> None:
        """Test getting the active profile."""
        profile = manager.get_active_profile()
        assert profile is not None
        assert profile.name == "default"

    def test_save_profile(self, manager: ProfileManager) -> None:
        """Test saving a profile."""
        profile = Profile(
            name="saved",
            display_name="Saved Profile",
            settings={"volume": 0.5},
        )
        manager.save_profile(profile)

        loaded = manager.get_profile("saved")
        assert loaded is not None
        assert loaded.display_name == "Saved Profile"
        assert loaded.volume == 0.5

    def test_create_profile(self, manager: ProfileManager) -> None:
        """Test creating a new profile."""
        profile = manager.create_profile(
            name="New Profile",
            display_name="My New Profile",
            description="Description",
        )
        assert profile.name == "new_profile"  # normalized
        assert profile.display_name == "My New Profile"
        assert profile.description == "Description"

    def test_create_profile_normalizes_name(self, manager: ProfileManager) -> None:
        """Test that profile names are normalized."""
        profile = manager.create_profile("My Custom Profile")
        assert profile.name == "my_custom_profile"

    def test_create_profile_duplicate_raises(self, manager: ProfileManager) -> None:
        """Test that creating a duplicate profile raises ValueError."""
        manager.create_profile("unique")
        with pytest.raises(ValueError, match="already exists"):
            manager.create_profile("unique")

    def test_create_profile_copy_from(self, manager: ProfileManager) -> None:
        """Test creating a profile by copying from another."""
        # Create source profile with custom settings
        source = manager.get_profile("default")
        assert source is not None
        source.volume = 0.7
        source.output_device_id = 5
        manager.save_profile(source)

        # Create copy
        copy = manager.create_profile("copy", copy_from="default")
        assert copy.volume == 0.7
        assert copy.output_device_id == 5

    def test_create_profile_copy_from_nonexistent(self, manager: ProfileManager) -> None:
        """Test that copying from nonexistent profile raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            manager.create_profile("copy", copy_from="nonexistent")

    def test_delete_profile(self, manager: ProfileManager) -> None:
        """Test deleting a profile."""
        manager.create_profile("to_delete")
        assert manager.delete_profile("to_delete")
        assert manager.get_profile("to_delete") is None

    def test_delete_profile_not_found(self, manager: ProfileManager) -> None:
        """Test deleting a non-existent profile returns False."""
        assert not manager.delete_profile("nonexistent")

    def test_delete_default_profile_raises(self, manager: ProfileManager) -> None:
        """Test that deleting the default profile raises ValueError."""
        with pytest.raises(ValueError, match="Cannot delete the default profile"):
            manager.delete_profile("default")

    def test_delete_active_profile_switches_to_default(self, manager: ProfileManager) -> None:
        """Test that deleting the active profile switches to default."""
        manager.create_profile("active_profile")
        manager.switch_profile("active_profile")
        assert manager.active_profile_name == "active_profile"

        manager.delete_profile("active_profile")
        assert manager.active_profile_name == "default"

    def test_switch_profile(self, manager: ProfileManager) -> None:
        """Test switching profiles."""
        manager.create_profile("other")
        profile = manager.switch_profile("other")

        assert profile is not None
        assert profile.name == "other"
        assert manager.active_profile_name == "other"

    def test_switch_profile_not_found(self, manager: ProfileManager) -> None:
        """Test switching to non-existent profile returns None."""
        profile = manager.switch_profile("nonexistent")
        assert profile is None
        assert manager.active_profile_name == "default"

    def test_set_default_profile(self, manager: ProfileManager) -> None:
        """Test setting default profile."""
        manager.create_profile("new_default")
        assert manager.set_default_profile("new_default")
        assert manager.default_profile_name == "new_default"

    def test_set_default_profile_not_found(self, manager: ProfileManager) -> None:
        """Test setting nonexistent profile as default returns False."""
        assert not manager.set_default_profile("nonexistent")

    def test_active_profile_name_property(self, manager: ProfileManager) -> None:
        """Test active_profile_name property."""
        assert manager.active_profile_name == "default"
        manager.active_profile_name = "other_value"
        assert manager.active_profile_name == "other_value"

    def test_default_profile_name_property(self, manager: ProfileManager) -> None:
        """Test default_profile_name property."""
        assert manager.default_profile_name == "default"
        manager.default_profile_name = "other_value"
        assert manager.default_profile_name == "other_value"


class TestLegacyConfigMigration:
    """Test legacy config migration."""

    @pytest.fixture
    def temp_base_dir(self) -> Generator[Path]:
        """Create a temporary base directory for testing.

        Yields:
            Path: Temporary directory path.

        """
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_migrate_legacy_config(self, temp_base_dir: Path) -> None:
        """Test that legacy config is migrated to profile format."""
        # Create legacy config (without version field - the key indicator of legacy format)
        config_file = temp_base_dir / "config.json"
        legacy_config = {
            "output_device_id": 3,
            "volume": 0.8,
            "sounds_dir": "/path/to/sounds",
            "hotkeys": {"<f1>": "sound1"},
            "hotkey_mode": "merged",
        }
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with config_file.open("w") as f:
            json.dump(legacy_config, f)

        # Initialize ProfileManager - should trigger migration
        manager = ProfileManager(base_dir=temp_base_dir)

        # Check migration
        profile = manager.get_profile("default")
        assert profile is not None
        assert profile.output_device_id == 3
        assert profile.volume == 0.8
        assert profile.sounds_dir == "/path/to/sounds"
        assert profile.hotkeys == {"<f1>": "sound1"}

        # Check backup was created
        backup_file = config_file.with_suffix(".json.legacy_backup")
        assert backup_file.exists()

    def test_already_migrated_config_not_remigrated(self, temp_base_dir: Path) -> None:
        """Test that already migrated config is not re-migrated."""
        # Create new-format config
        config_file = temp_base_dir / "config.json"
        new_config = {
            "version": 2,
            "default_profile": "default",
            "active_profile": "custom",
            "global_settings": {},
        }
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with config_file.open("w") as f:
            json.dump(new_config, f)

        # Create profiles directory with default profile
        profiles_dir = temp_base_dir / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        default_profile = {
            "name": "default",
            "settings": {"volume": 0.5},
        }
        with (profiles_dir / "default.json").open("w") as f:
            json.dump(default_profile, f)

        # Initialize ProfileManager
        manager = ProfileManager(base_dir=temp_base_dir)

        # Check that active profile setting was preserved
        assert manager.active_profile_name == "custom"
        # Check that profile settings were preserved
        profile = manager.get_profile("default")
        assert profile is not None
        assert profile.volume == 0.5
