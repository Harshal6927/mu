# Copyright (c) 2025. All rights reserved.
"""Profile management for MUC Soundboard."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Profile:
    """A configuration profile."""

    name: str
    display_name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize display name if not provided."""
        if not self.display_name:
            self.display_name = self.name.replace("_", " ").title()

    @property
    def output_device_id(self) -> int | None:
        """Get output device ID."""
        return self.settings.get("output_device_id")

    @output_device_id.setter
    def output_device_id(self, value: int | None) -> None:
        """Set output device ID."""
        self.settings["output_device_id"] = value

    @property
    def volume(self) -> float:
        """Get volume level."""
        return self.settings.get("volume", 1.0)

    @volume.setter
    def volume(self, value: float) -> None:
        """Set volume level."""
        self.settings["volume"] = value

    @property
    def sounds_dir(self) -> str | None:
        """Get sounds directory."""
        return self.settings.get("sounds_dir")

    @sounds_dir.setter
    def sounds_dir(self, value: str) -> None:
        """Set sounds directory."""
        self.settings["sounds_dir"] = value

    @property
    def sounds_dirs(self) -> list[str]:
        """Get multiple sounds directories."""
        dirs = self.settings.get("sounds_dirs", [])
        if not dirs and self.sounds_dir:
            return [self.sounds_dir]
        return dirs

    @sounds_dirs.setter
    def sounds_dirs(self, value: list[str]) -> None:
        """Set multiple sounds directories."""
        self.settings["sounds_dirs"] = value

    @property
    def hotkeys(self) -> dict[str, str]:
        """Get hotkey bindings."""
        return self.settings.get("hotkeys", {})

    @hotkeys.setter
    def hotkeys(self, value: dict[str, str]) -> None:
        """Set hotkey bindings."""
        self.settings["hotkeys"] = value

    @property
    def hotkey_mode(self) -> str:
        """Get hotkey mode."""
        return self.settings.get("hotkey_mode", "merged")

    @hotkey_mode.setter
    def hotkey_mode(self, value: str) -> None:
        """Set hotkey mode."""
        self.settings["hotkey_mode"] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary for JSON serialization.

        Returns:
            Dictionary representation of profile

        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        """Create Profile from dictionary.

        Args:
            data: Dictionary with profile fields

        Returns:
            Profile instance

        """
        return cls(
            name=data["name"],
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(tz=UTC).isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(tz=UTC).isoformat())),
            settings=data.get("settings", {}),
        )


class ProfileManager:
    """Manages configuration profiles."""

    CONFIG_VERSION = 2

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize ProfileManager.

        Args:
            base_dir: Base directory for MUC config (default: ~/.muc)

        """
        self.base_dir = base_dir or (Path.home() / ".muc")
        self.profiles_dir = self.base_dir / "profiles"
        self.config_file = self.base_dir / "config.json"

        self._ensure_directories()
        self._global_config = self._load_global_config()

        # Migrate legacy config if needed
        self._migrate_legacy_config()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _migrate_legacy_config(self) -> None:
        """Migrate legacy config.json to profile format if needed."""
        if not self.config_file.exists():
            # No config at all, create default profile
            if not list(self.profiles_dir.glob("*.json")):
                self._create_default_profile()
            return

        # Check if already migrated
        if "version" in self._global_config and self._global_config.get("version", 0) >= self.CONFIG_VERSION:
            # Already migrated, ensure default profile exists
            if not list(self.profiles_dir.glob("*.json")):
                self._create_default_profile()
            return

        # Load old config
        try:
            with self.config_file.open(encoding="utf-8") as f:
                old_config = json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read legacy config for migration")
            self._create_default_profile()
            return

        # Skip if it's already the new format
        if "version" in old_config:
            return

        logger.info("Migrating legacy configuration to profile format")

        # Create default profile from old config
        profile = Profile(
            name="default",
            display_name="Default",
            description="Migrated from legacy configuration",
            settings={
                "output_device_id": old_config.get("output_device_id"),
                "volume": old_config.get("volume", 1.0),
                "sounds_dir": old_config.get("sounds_dir"),
                "hotkeys": old_config.get("hotkeys", {}),
                "hotkey_mode": old_config.get("hotkey_mode", "merged"),
            },
        )

        # Save profile
        self.save_profile(profile)

        # Backup old config
        backup_path = self.config_file.with_suffix(".json.legacy_backup")
        try:
            self.config_file.rename(backup_path)
            logger.info(f"Legacy config backed up to {backup_path}")
        except OSError as e:
            logger.warning(f"Could not backup legacy config: {e}")

        # Create new global config
        self._global_config = {
            "version": self.CONFIG_VERSION,
            "default_profile": "default",
            "active_profile": "default",
            "global_settings": {},
        }
        self._save_global_config()

        logger.info("Migration complete")

    def _create_default_profile(self) -> None:
        """Create the default profile."""
        default = Profile(
            name="default",
            display_name="Default",
            description="Default configuration profile",
            settings={
                "output_device_id": None,
                "volume": 1.0,
                "sounds_dir": str(Path.cwd() / "sounds"),
                "hotkeys": {},
                "hotkey_mode": "merged",
            },
        )
        self.save_profile(default)
        logger.info("Created default profile")

    def _load_global_config(self) -> dict[str, Any]:
        """Load global configuration.

        Returns:
            Global configuration dictionary

        """
        if self.config_file.exists():
            try:
                with self.config_file.open(encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
            else:
                # Only return if it's the new format (has version key)
                if "version" in data and data.get("version", 0) >= self.CONFIG_VERSION:
                    return data
                # Legacy config exists - return without version so migration triggers
                return {"_legacy_exists": True}
        return {
            "version": self.CONFIG_VERSION,
            "default_profile": "default",
            "active_profile": "default",
            "global_settings": {},
        }

    def _save_global_config(self) -> None:
        """Save global configuration."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(self._global_config, f, indent=2)

    @property
    def active_profile_name(self) -> str:
        """Get the active profile name."""
        return self._global_config.get("active_profile", "default")

    @active_profile_name.setter
    def active_profile_name(self, name: str) -> None:
        """Set the active profile name."""
        self._global_config["active_profile"] = name
        self._save_global_config()

    @property
    def default_profile_name(self) -> str:
        """Get the default profile name."""
        return self._global_config.get("default_profile", "default")

    @default_profile_name.setter
    def default_profile_name(self, name: str) -> None:
        """Set the default profile name."""
        self._global_config["default_profile"] = name
        self._save_global_config()

    def list_profiles(self) -> list[str]:
        """List all profile names.

        Returns:
            List of profile names

        """
        return [f.stem for f in self.profiles_dir.glob("*.json")]

    def get_profile(self, name: str) -> Profile | None:
        """Load a profile by name.

        Args:
            name: Profile name

        Returns:
            Profile if found, None otherwise

        """
        profile_file = self.profiles_dir / f"{name}.json"
        if not profile_file.exists():
            return None

        try:
            with profile_file.open(encoding="utf-8") as f:
                data = json.load(f)
            return Profile.from_dict(data)
        except (json.JSONDecodeError, OSError):
            logger.exception(f"Failed to load profile {name}")
            return None

    def get_active_profile(self) -> Profile:
        """Get the currently active profile.

        Returns:
            Active Profile (falls back to default if not found)

        """
        profile = self.get_profile(self.active_profile_name)
        if profile is None:
            # Fallback to default
            profile = self.get_profile("default")
        if profile is None:
            # Create default if missing
            self._create_default_profile()
            profile = self.get_profile("default")
        return profile  # type: ignore[return-value]

    def save_profile(self, profile: Profile) -> None:
        """Save a profile.

        Args:
            profile: Profile to save

        """
        profile.updated_at = datetime.now(tz=UTC)
        profile_file = self.profiles_dir / f"{profile.name}.json"
        with profile_file.open("w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)
        logger.info(f"Saved profile: {profile.name}")

    def create_profile(
        self,
        name: str,
        display_name: str = "",
        description: str = "",
        copy_from: str | None = None,
    ) -> Profile:
        """Create a new profile.

        Args:
            name: Profile name (will be normalized)
            display_name: Human-readable display name
            description: Profile description
            copy_from: Name of profile to copy settings from

        Returns:
            Created Profile

        Raises:
            ValueError: If profile already exists or source profile not found

        """
        name = name.lower().replace(" ", "_")

        if self.get_profile(name):
            raise ValueError(f"Profile '{name}' already exists")

        if copy_from:
            source = self.get_profile(copy_from)
            if source is None:
                raise ValueError(f"Source profile '{copy_from}' not found")
            profile = Profile(
                name=name,
                display_name=display_name or name.replace("_", " ").title(),
                description=description,
                settings=source.settings.copy(),
            )
        else:
            profile = Profile(
                name=name,
                display_name=display_name or name.replace("_", " ").title(),
                description=description,
                settings={
                    "output_device_id": None,
                    "volume": 1.0,
                    "sounds_dir": str(Path.cwd() / "sounds"),
                    "hotkeys": {},
                    "hotkey_mode": "merged",
                },
            )

        self.save_profile(profile)
        logger.info(f"Created profile: {name}")
        return profile

    def delete_profile(self, name: str) -> bool:
        """Delete a profile.

        Args:
            name: Profile name to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete the default profile

        """
        if name == "default":
            raise ValueError("Cannot delete the default profile")

        profile_file = self.profiles_dir / f"{name}.json"
        if not profile_file.exists():
            return False

        profile_file.unlink()

        # If deleted profile was active, switch to default
        if self.active_profile_name == name:
            self.active_profile_name = "default"

        logger.info(f"Deleted profile: {name}")
        return True

    def switch_profile(self, name: str) -> Profile | None:
        """Switch to a different profile.

        Args:
            name: Profile name to switch to

        Returns:
            Profile if found and switched, None otherwise

        """
        profile = self.get_profile(name)
        if profile is None:
            return None

        self.active_profile_name = name
        logger.info(f"Switched to profile: {name}")
        return profile

    def set_default_profile(self, name: str) -> bool:
        """Set the default profile.

        Args:
            name: Profile name to set as default

        Returns:
            True if set, False if profile not found

        """
        if self.get_profile(name) is None:
            return False

        self.default_profile_name = name
        logger.info(f"Set default profile: {name}")
        return True
