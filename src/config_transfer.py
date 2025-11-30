# Copyright (c) 2025. All rights reserved.
"""Configuration export/import functionality for MUC Soundboard."""

import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from src.logging_config import get_logger
from src.profile_manager import Profile, ProfileManager

logger = get_logger(__name__)


class ConfigTransfer:
    """Handles configuration export and import."""

    EXPORT_VERSION = 1

    def __init__(self, profile_manager: ProfileManager | None = None) -> None:
        """Initialize ConfigTransfer.

        Args:
            profile_manager: ProfileManager instance (creates new if None)

        """
        self.profile_manager = profile_manager or ProfileManager()

    def export_profile(
        self,
        profile_name: str,
        output_path: Path,
        *,
        include_hotkeys: bool = True,
        portable_paths: bool = True,
    ) -> Path:
        """Export a single profile to a JSON file.

        Args:
            profile_name: Name of profile to export
            output_path: Output file path
            include_hotkeys: Whether to include hotkey bindings
            portable_paths: Convert absolute paths to relative/placeholder

        Returns:
            Path to the exported file

        Raises:
            ValueError: If profile not found

        """
        profile = self.profile_manager.get_profile(profile_name)
        if not profile:
            raise ValueError(f"Profile '{profile_name}' not found")

        export_data = {
            "_export_version": self.EXPORT_VERSION,
            "_exported_at": datetime.now(tz=UTC).isoformat(),
            "_source_platform": self._get_platform(),
            "profile": profile.to_dict(),
        }

        # Optionally remove hotkeys
        if not include_hotkeys:
            export_data["profile"]["settings"].pop("hotkeys", None)

        # Convert paths to portable format
        if portable_paths:
            settings = export_data["profile"]["settings"]
            if settings.get("sounds_dir"):
                sounds_dir = Path(settings["sounds_dir"])
                if sounds_dir.exists():
                    settings["sounds_dir"] = f"$SOUNDS_DIR/{sounds_dir.name}"
                else:
                    settings["sounds_dir"] = "$SOUNDS_DIR"

            if "sounds_dirs" in settings:
                portable_dirs = []
                for dir_path in settings["sounds_dirs"]:
                    path = Path(dir_path)
                    if path.exists():
                        portable_dirs.append(f"$SOUNDS_DIR/{path.name}")
                    else:
                        portable_dirs.append("$SOUNDS_DIR")
                settings["sounds_dirs"] = portable_dirs

        # Ensure output has .json extension
        if output_path.suffix != ".json":
            output_path = output_path.with_suffix(".json")

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported profile '{profile_name}' to {output_path}")
        return output_path

    def export_all(self, output_path: Path) -> Path:
        """Export all profiles to a ZIP archive.

        Args:
            output_path: Output archive path

        Returns:
            Path to the exported archive

        """
        if output_path.suffix != ".zip":
            output_path = output_path.with_suffix(".zip")

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Export each profile
            for name in self.profile_manager.list_profiles():
                profile = self.profile_manager.get_profile(name)
                if profile:
                    profile_data = {
                        "_export_version": self.EXPORT_VERSION,
                        "profile": profile.to_dict(),
                    }
                    zf.writestr(
                        f"profiles/{name}.json",
                        json.dumps(profile_data, indent=2),
                    )

            # Export manifest with global config info
            manifest = {
                "_export_version": self.EXPORT_VERSION,
                "_exported_at": datetime.now(tz=UTC).isoformat(),
                "_source_platform": self._get_platform(),
                "active_profile": self.profile_manager.active_profile_name,
                "default_profile": self.profile_manager.default_profile_name,
                "profiles": self.profile_manager.list_profiles(),
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        logger.info(f"Exported all profiles to {output_path}")
        return output_path

    def import_profile(
        self,
        input_path: Path,
        new_name: str | None = None,
        *,
        overwrite: bool = False,
        sounds_dir: Path | None = None,
    ) -> Profile:
        """Import a profile from a JSON file.

        Args:
            input_path: Path to the export file
            new_name: Optional new name for the profile
            overwrite: Whether to overwrite existing profile
            sounds_dir: Path to use for sounds directory

        Returns:
            The imported Profile

        Raises:
            ValueError: If export version incompatible or profile exists without overwrite

        """
        with input_path.open(encoding="utf-8") as f:
            data = json.load(f)

        # Validate export version
        version = data.get("_export_version", 0)
        if version > self.EXPORT_VERSION:
            raise ValueError(f"Export version {version} is newer than supported ({self.EXPORT_VERSION})")

        profile_data = data.get("profile", {})

        # Apply new name if provided
        if new_name:
            profile_data["name"] = new_name.lower().replace(" ", "_")

        # Resolve portable paths
        settings = profile_data.get("settings", {})
        default_sounds_dir = str(sounds_dir) if sounds_dir else str(Path.cwd() / "sounds")

        if "sounds_dir" in settings:
            sounds_path = settings["sounds_dir"]
            if sounds_path and sounds_path.startswith("$SOUNDS_DIR"):
                settings["sounds_dir"] = default_sounds_dir

        if "sounds_dirs" in settings:
            resolved_dirs = []
            for dir_path in settings["sounds_dirs"]:
                if dir_path.startswith("$SOUNDS_DIR"):
                    resolved_dirs.append(default_sounds_dir)
                else:
                    resolved_dirs.append(dir_path)
            settings["sounds_dirs"] = resolved_dirs

        # Check for existing
        name = profile_data.get("name", "imported")
        if self.profile_manager.get_profile(name) and not overwrite:
            raise ValueError(f"Profile '{name}' already exists. Use --overwrite to replace.")

        profile = Profile.from_dict(profile_data)
        self.profile_manager.save_profile(profile)

        logger.info(f"Imported profile: {profile.name}")
        return profile

    def import_all(
        self,
        archive_path: Path,
        *,
        overwrite: bool = False,
    ) -> list[str]:
        """Import all profiles from a ZIP archive.

        Args:
            archive_path: Path to the archive
            overwrite: Whether to overwrite existing profiles

        Returns:
            List of imported profile names

        """
        imported = []

        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                if name.startswith("profiles/") and name.endswith(".json"):
                    content = zf.read(name).decode("utf-8")
                    data = json.loads(content)
                    profile_data = data.get("profile", {})

                    profile_name = profile_data.get("name", Path(name).stem)

                    if self.profile_manager.get_profile(profile_name) and not overwrite:
                        logger.warning(f"Skipping existing profile: {profile_name}")
                        continue

                    profile = Profile.from_dict(profile_data)
                    self.profile_manager.save_profile(profile)
                    imported.append(profile_name)

        logger.info(f"Imported {len(imported)} profiles")
        return imported

    @staticmethod
    def _get_platform() -> str:
        """Get current platform identifier.

        Returns:
            Platform identifier string

        """
        return sys.platform
