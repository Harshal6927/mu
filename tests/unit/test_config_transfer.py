# Copyright (c) 2025. All rights reserved.
"""Tests for config transfer module."""

import json
import tempfile
import zipfile
from collections.abc import Generator
from pathlib import Path

import pytest

from src.config_transfer import ConfigTransfer
from src.profile_manager import ProfileManager


class TestConfigTransfer:
    """Test the ConfigTransfer class."""

    @pytest.fixture
    def temp_base_dir(self) -> Generator[Path]:
        """Create a temporary base directory for testing.

        Yields:
            Path: Temporary directory path.

        """
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_output_dir(self) -> Generator[Path]:
        """Create a temporary output directory for testing.

        Yields:
            Path: Temporary output directory path.

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

    @pytest.fixture
    def transfer(self, manager: ProfileManager) -> ConfigTransfer:
        """Create a ConfigTransfer instance.

        Returns:
            ConfigTransfer: Transfer instance for testing.

        """
        return ConfigTransfer(profile_manager=manager)

    def test_export_profile_basic(self, transfer: ConfigTransfer, temp_output_dir: Path) -> None:
        """Test basic profile export."""
        output_path = temp_output_dir / "export.json"
        result = transfer.export_profile("default", output_path)

        assert result.exists()
        assert result.suffix == ".json"

        with result.open() as f:
            data = json.load(f)

        assert "_export_version" in data
        assert "_exported_at" in data
        assert "profile" in data
        assert data["profile"]["name"] == "default"

    def test_export_profile_adds_json_extension(self, transfer: ConfigTransfer, temp_output_dir: Path) -> None:
        """Test that .json extension is added if missing."""
        output_path = temp_output_dir / "export"  # No extension
        result = transfer.export_profile("default", output_path)
        assert result.suffix == ".json"

    def test_export_profile_not_found(self, transfer: ConfigTransfer, temp_output_dir: Path) -> None:
        """Test exporting non-existent profile raises ValueError."""
        output_path = temp_output_dir / "export.json"
        with pytest.raises(ValueError, match="not found"):
            transfer.export_profile("nonexistent", output_path)

    def test_export_profile_without_hotkeys(
        self,
        transfer: ConfigTransfer,
        manager: ProfileManager,
        temp_output_dir: Path,
    ) -> None:
        """Test exporting profile without hotkeys."""
        # Add hotkeys to default profile
        profile = manager.get_profile("default")
        assert profile is not None
        profile.hotkeys = {"<f1>": "sound1"}
        manager.save_profile(profile)

        output_path = temp_output_dir / "export.json"
        transfer.export_profile("default", output_path, include_hotkeys=False)

        with output_path.open() as f:
            data = json.load(f)

        assert "hotkeys" not in data["profile"]["settings"]

    def test_export_profile_portable_paths(
        self,
        transfer: ConfigTransfer,
        manager: ProfileManager,
        temp_base_dir: Path,
        temp_output_dir: Path,
    ) -> None:
        """Test that paths are converted to portable format."""
        # Create a sounds directory that exists
        sounds_dir = temp_base_dir / "sounds"
        sounds_dir.mkdir()

        profile = manager.get_profile("default")
        assert profile is not None
        profile.sounds_dir = str(sounds_dir)
        manager.save_profile(profile)

        output_path = temp_output_dir / "export.json"
        transfer.export_profile("default", output_path, portable_paths=True)

        with output_path.open() as f:
            data = json.load(f)

        assert data["profile"]["settings"]["sounds_dir"].startswith("$SOUNDS_DIR")

    def test_export_all(self, transfer: ConfigTransfer, manager: ProfileManager, temp_output_dir: Path) -> None:
        """Test exporting all profiles to archive."""
        # Create additional profiles
        manager.create_profile("profile1")
        manager.create_profile("profile2")

        output_path = temp_output_dir / "backup.zip"
        result = transfer.export_all(output_path)

        assert result.exists()
        assert result.suffix == ".zip"

        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "profiles/default.json" in names
            assert "profiles/profile1.json" in names
            assert "profiles/profile2.json" in names

    def test_import_profile_basic(
        self,
        transfer: ConfigTransfer,
        manager: ProfileManager,
        temp_output_dir: Path,
    ) -> None:
        """Test basic profile import."""
        # Export first
        output_path = temp_output_dir / "export.json"
        transfer.export_profile("default", output_path)

        # Import with new name (can't delete default profile)
        profile = transfer.import_profile(output_path, new_name="imported")

        assert profile.name == "imported"
        loaded = manager.get_profile("imported")
        assert loaded is not None

    def test_import_profile_with_new_name(self, transfer: ConfigTransfer, temp_output_dir: Path) -> None:
        """Test importing profile with a new name."""
        output_path = temp_output_dir / "export.json"
        transfer.export_profile("default", output_path)

        profile = transfer.import_profile(output_path, new_name="new_name")
        assert profile.name == "new_name"

    def test_import_profile_overwrite(
        self,
        transfer: ConfigTransfer,
        manager: ProfileManager,
        temp_output_dir: Path,
    ) -> None:
        """Test importing profile with overwrite."""
        # Create export
        output_path = temp_output_dir / "export.json"
        transfer.export_profile("default", output_path)

        # Create profile to overwrite
        manager.create_profile("to_overwrite")

        # Import with overwrite
        profile = transfer.import_profile(output_path, new_name="to_overwrite", overwrite=True)
        assert profile.name == "to_overwrite"

    def test_import_profile_no_overwrite_raises(
        self,
        transfer: ConfigTransfer,
        temp_output_dir: Path,
    ) -> None:
        """Test that importing without overwrite raises for existing profile."""
        output_path = temp_output_dir / "export.json"
        transfer.export_profile("default", output_path)

        # Try to import with same name as default
        with pytest.raises(ValueError, match="already exists"):
            transfer.import_profile(output_path)

    def test_import_profile_resolves_portable_paths(
        self,
        transfer: ConfigTransfer,
        temp_output_dir: Path,
    ) -> None:
        """Test that portable paths are resolved on import."""
        # Create export with portable path
        export_data = {
            "_export_version": 1,
            "profile": {
                "name": "portable",
                "settings": {"sounds_dir": "$SOUNDS_DIR/mysounds"},
            },
        }
        export_file = temp_output_dir / "portable.json"
        with export_file.open("w") as f:
            json.dump(export_data, f)

        custom_sounds = temp_output_dir / "custom_sounds"
        profile = transfer.import_profile(export_file, sounds_dir=custom_sounds)

        assert profile.sounds_dir == str(custom_sounds)

    def test_import_all(self, transfer: ConfigTransfer, manager: ProfileManager, temp_output_dir: Path) -> None:
        """Test importing all profiles from archive."""
        # Create profiles and export
        manager.create_profile("export1")
        manager.create_profile("export2")

        archive_path = temp_output_dir / "backup.zip"
        transfer.export_all(archive_path)

        # Delete profiles (except default)
        manager.delete_profile("export1")
        manager.delete_profile("export2")

        # Import
        imported = transfer.import_all(archive_path)

        assert "export1" in imported
        assert "export2" in imported
        assert manager.get_profile("export1") is not None
        assert manager.get_profile("export2") is not None

    def test_import_all_skips_existing(
        self,
        transfer: ConfigTransfer,
        manager: ProfileManager,
        temp_output_dir: Path,
    ) -> None:
        """Test that import_all skips existing profiles without overwrite."""
        manager.create_profile("existing")

        archive_path = temp_output_dir / "backup.zip"
        transfer.export_all(archive_path)

        # Import without overwrite - should skip existing
        imported = transfer.import_all(archive_path, overwrite=False)

        # "existing" should not be in imported list (already existed)
        # "default" should also not be in imported (already existed)
        # Only newly imported profiles should be in the list
        assert len([p for p in imported if p == "existing"]) == 0

    def test_version_check_on_import(self, transfer: ConfigTransfer, temp_output_dir: Path) -> None:
        """Test that future export versions raise ValueError."""
        export_data = {
            "_export_version": 999,  # Future version
            "profile": {"name": "future"},
        }
        export_file = temp_output_dir / "future.json"
        with export_file.open("w") as f:
            json.dump(export_data, f)

        with pytest.raises(ValueError, match="newer than supported"):
            transfer.import_profile(export_file)

    def test_get_platform(self) -> None:
        """Test _get_platform returns a string."""
        platform = ConfigTransfer._get_platform()
        assert isinstance(platform, str)
        assert len(platform) > 0
