# Copyright (c) 2025. All rights reserved.
"""Configuration management for muc soundboard."""

import json
from pathlib import Path

from .exceptions import ConfigCorruptedError
from .logging_config import get_logger
from .validators import validate_config_data

logger = get_logger(__name__)


class Config:
    """Manages application configuration."""

    def __init__(self) -> None:
        """Initialize the Config with default values and load existing config."""
        self.config_file = Path.home() / ".muc" / "config.json"
        self.sounds_dir = Path.cwd() / "sounds"
        self.output_device_id: int | None = None
        self.volume: float = 1.0
        self.hotkeys: dict[str, str] = {}
        self.hotkey_mode: str = "merged"  # "default" | "custom" | "merged"

        # Load existing config if it exists
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        logger.debug(f"Loading config from {self.config_file}")

        if not self.config_file.exists():
            logger.info("No config file found, using defaults")
            return

        try:
            with self.config_file.open(encoding="utf-8") as f:
                raw_data = json.load(f)

            # Validate the loaded data
            data = validate_config_data(raw_data)

            self.output_device_id = data.get("output_device_id")
            self.volume = data.get("volume", 1.0)
            if "sounds_dir" in data:
                self.sounds_dir = Path(data["sounds_dir"])
            self.hotkeys = data.get("hotkeys", {})
            self.hotkey_mode = data.get("hotkey_mode", "merged")

            logger.info(f"Config loaded: device={self.output_device_id}, volume={self.volume}")

        except json.JSONDecodeError:
            logger.exception("Config file corrupted")
            # Create backup of corrupted file
            self._backup_corrupted_config()
            # Continue with defaults

        except OSError:
            logger.exception("Cannot read config file")
            # Continue with defaults

    def _backup_corrupted_config(self) -> None:
        """Backup a corrupted config file."""
        if self.config_file.exists():
            backup_path = self.config_file.with_suffix(".json.bak")
            try:
                self.config_file.rename(backup_path)
                logger.info(f"Corrupted config backed up to {backup_path}")
            except OSError as e:
                logger.warning(f"Could not backup config: {e}")

    def save(self) -> None:
        """Save configuration to file."""
        logger.debug("Saving configuration")

        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "output_device_id": self.output_device_id,
            "sounds_dir": str(self.sounds_dir),
            "volume": self.volume,
            "hotkeys": self.hotkeys,
            "hotkey_mode": self.hotkey_mode,
        }

        try:
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Configuration saved successfully")
        except OSError as e:
            logger.exception("Failed to save config")
            raise ConfigCorruptedError(
                f"Cannot save configuration: {e}",
                suggestion="Check write permissions for ~/.muc/",
            ) from e
