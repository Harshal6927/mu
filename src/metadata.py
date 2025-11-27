# Copyright (c) 2025. All rights reserved.
"""Sound metadata management for tags, favorites, and play statistics."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SoundMetadata:
    """Metadata for a single sound."""

    tags: list[str] = field(default_factory=list)
    volume: float = 1.0
    favorite: bool = False
    play_count: int = 0
    last_played: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of metadata

        """
        return {
            "tags": self.tags,
            "volume": self.volume,
            "favorite": self.favorite,
            "play_count": self.play_count,
            "last_played": self.last_played.isoformat() if self.last_played else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SoundMetadata":
        """Create SoundMetadata from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            SoundMetadata instance

        """
        last_played = data.get("last_played")
        if last_played:
            last_played = datetime.fromisoformat(last_played)
        return cls(
            tags=data.get("tags", []),
            volume=data.get("volume", 1.0),
            favorite=data.get("favorite", False),
            play_count=data.get("play_count", 0),
            last_played=last_played,
        )


class MetadataManager:
    """Manages sound metadata storage."""

    def __init__(self, metadata_file: Path | None = None) -> None:
        """Initialize MetadataManager.

        Args:
            metadata_file: Path to metadata JSON file (default: ~/.muc/metadata.json)

        """
        self.metadata_file = metadata_file or (Path.home() / ".muc" / "metadata.json")
        self.sounds: dict[str, SoundMetadata] = {}
        self.all_tags: set[str] = set()
        self.load()

    def load(self) -> None:
        """Load metadata from file."""
        logger.debug(f"Loading metadata from {self.metadata_file}")

        if not self.metadata_file.exists():
            logger.info("No metadata file found, starting fresh")
            return

        try:
            with self.metadata_file.open(encoding="utf-8") as f:
                data = json.load(f)
                for name, sound_data in data.get("sounds", {}).items():
                    self.sounds[name] = SoundMetadata.from_dict(sound_data)
                self.all_tags = set(data.get("tags", []))
            logger.info(f"Loaded metadata for {len(self.sounds)} sounds")
        except json.JSONDecodeError:
            logger.exception("Metadata file corrupted, starting fresh")
        except OSError:
            logger.exception("Cannot read metadata file")

    def save(self) -> None:
        """Save metadata to file."""
        logger.debug("Saving metadata")

        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "sounds": {name: meta.to_dict() for name, meta in self.sounds.items()},
            "tags": sorted(self.all_tags),
        }

        try:
            with self.metadata_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug("Metadata saved successfully")
        except OSError:
            logger.exception("Failed to save metadata")

    def get_metadata(self, sound_name: str) -> SoundMetadata:
        """Get metadata for a sound, creating default if not exists.

        Args:
            sound_name: Name of the sound

        Returns:
            SoundMetadata for the sound

        """
        if sound_name not in self.sounds:
            self.sounds[sound_name] = SoundMetadata()
        return self.sounds[sound_name]

    def add_tag(self, sound_name: str, tag: str) -> bool:
        """Add a tag to a sound.

        Args:
            sound_name: Name of the sound
            tag: Tag to add

        Returns:
            True if tag was added (not a duplicate)

        """
        meta = self.get_metadata(sound_name)
        tag = tag.lower().strip()
        if tag and tag not in meta.tags:
            meta.tags.append(tag)
            self.all_tags.add(tag)
            self.save()
            logger.debug(f"Added tag '{tag}' to '{sound_name}'")
            return True
        return False

    def remove_tag(self, sound_name: str, tag: str) -> bool:
        """Remove a tag from a sound.

        Args:
            sound_name: Name of the sound
            tag: Tag to remove

        Returns:
            True if tag was removed

        """
        meta = self.get_metadata(sound_name)
        tag = tag.lower().strip()
        if tag in meta.tags:
            meta.tags.remove(tag)
            self.save()
            logger.debug(f"Removed tag '{tag}' from '{sound_name}'")
            return True
        return False

    def get_sounds_by_tag(self, tag: str) -> list[str]:
        """Get all sounds with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of sound names with the tag

        """
        tag = tag.lower().strip()
        return [name for name, meta in self.sounds.items() if tag in meta.tags]

    def get_sounds_by_tags(self, tags: list[str]) -> list[str]:
        """Get all sounds with any of the specified tags (OR logic).

        Args:
            tags: List of tags to filter by

        Returns:
            List of sound names with any of the tags

        """
        tags = [t.lower().strip() for t in tags]
        return [name for name, meta in self.sounds.items() if any(t in meta.tags for t in tags)]

    def get_favorites(self) -> list[str]:
        """Get all favorite sounds.

        Returns:
            List of favorite sound names

        """
        return [name for name, meta in self.sounds.items() if meta.favorite]

    def set_favorite(self, sound_name: str, *, is_favorite: bool) -> None:
        """Set favorite status for a sound.

        Args:
            sound_name: Name of the sound
            is_favorite: Whether to mark as favorite

        """
        meta = self.get_metadata(sound_name)
        meta.favorite = is_favorite
        self.save()
        logger.debug(f"Set '{sound_name}' favorite={is_favorite}")

    def toggle_favorite(self, sound_name: str) -> bool:
        """Toggle favorite status for a sound.

        Args:
            sound_name: Name of the sound

        Returns:
            New favorite status

        """
        meta = self.get_metadata(sound_name)
        meta.favorite = not meta.favorite
        self.save()
        logger.debug(f"Toggled '{sound_name}' favorite={meta.favorite}")
        return meta.favorite

    def set_volume(self, sound_name: str, volume: float) -> None:
        """Set volume for a specific sound.

        Args:
            sound_name: Name of the sound
            volume: Volume level (0.0 to 2.0)

        """
        meta = self.get_metadata(sound_name)
        meta.volume = max(0.0, min(2.0, volume))
        self.save()
        logger.debug(f"Set '{sound_name}' volume={meta.volume}")

    def record_play(self, sound_name: str) -> None:
        """Record that a sound was played.

        Args:
            sound_name: Name of the sound that was played

        """
        meta = self.get_metadata(sound_name)
        meta.play_count += 1
        meta.last_played = datetime.now(tz=UTC)
        self.save()
        logger.debug(f"Recorded play for '{sound_name}' (count={meta.play_count})")

    def get_all_tags_with_counts(self) -> dict[str, int]:
        """Get all tags with their usage counts.

        Returns:
            Dictionary mapping tag names to counts

        """
        tag_counts: dict[str, int] = {}
        for meta in self.sounds.values():
            for tag in meta.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return tag_counts

    def cleanup_unused_tags(self) -> int:
        """Remove tags that are no longer used by any sound.

        Returns:
            Number of tags removed

        """
        used_tags = set()
        for meta in self.sounds.values():
            used_tags.update(meta.tags)

        removed = len(self.all_tags - used_tags)
        self.all_tags = used_tags
        self.save()
        return removed
