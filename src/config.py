"""Configuration management for mu soundboard."""

import json
from pathlib import Path


class Config:
    """Manages application configuration."""

    def __init__(self):
        self.config_file = Path.home() / ".mu" / "config.json"
        self.sounds_dir = Path.cwd() / "sounds"
        self.output_device_id: int | None = None

        # Load existing config if it exists
        self.load()

    def load(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.output_device_id = data.get("output_device_id")
                    if "sounds_dir" in data:
                        self.sounds_dir = Path(data["sounds_dir"])
            except (json.JSONDecodeError, OSError):
                pass  # Use defaults

    def save(self):
        """Save configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "output_device_id": self.output_device_id,
            "sounds_dir": str(self.sounds_dir),
        }

        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)
