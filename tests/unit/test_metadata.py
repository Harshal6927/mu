# Copyright (c) 2025. All rights reserved.
# ruff: noqa: DOC201, DOC402
"""Unit tests for the metadata module."""

import tempfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.metadata import MetadataManager, SoundMetadata


@pytest.fixture
def temp_metadata_file() -> Generator[Path]:
    """Create a temporary metadata file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / ".muc" / "metadata.json"


@pytest.fixture
def metadata_manager(temp_metadata_file: Path) -> MetadataManager:
    """Create a MetadataManager with a temporary file."""
    return MetadataManager(metadata_file=temp_metadata_file)


class TestSoundMetadata:
    """Tests for SoundMetadata dataclass."""

    def test_default_values(self) -> None:
        """Test default values for SoundMetadata."""
        meta = SoundMetadata()
        assert meta.tags == []
        assert meta.volume == 1.0
        assert meta.favorite is False
        assert meta.play_count == 0
        assert meta.last_played is None

    def test_to_dict(self) -> None:
        """Test to_dict serialization."""
        now = datetime.now(tz=UTC)
        meta = SoundMetadata(
            tags=["meme", "loud"],
            volume=0.8,
            favorite=True,
            play_count=42,
            last_played=now,
        )
        data = meta.to_dict()

        assert data["tags"] == ["meme", "loud"]
        assert data["volume"] == 0.8
        assert data["favorite"] is True
        assert data["play_count"] == 42
        assert data["last_played"] == now.isoformat()

    def test_to_dict_none_last_played(self) -> None:
        """Test to_dict with None last_played."""
        meta = SoundMetadata()
        data = meta.to_dict()
        assert data["last_played"] is None

    def test_from_dict(self) -> None:
        """Test from_dict deserialization."""
        data = {
            "tags": ["effect", "gaming"],
            "volume": 1.5,
            "favorite": True,
            "play_count": 100,
            "last_played": "2025-11-25T10:30:00+00:00",
        }
        meta = SoundMetadata.from_dict(data)

        assert meta.tags == ["effect", "gaming"]
        assert meta.volume == 1.5
        assert meta.favorite is True
        assert meta.play_count == 100
        assert meta.last_played is not None

    def test_from_dict_with_defaults(self) -> None:
        """Test from_dict with minimal data uses defaults."""
        meta = SoundMetadata.from_dict({})
        assert meta.tags == []
        assert meta.volume == 1.0
        assert meta.favorite is False
        assert meta.play_count == 0
        assert meta.last_played is None


class TestMetadataManager:
    """Tests for MetadataManager class."""

    def test_init_creates_empty_state(self, metadata_manager: MetadataManager) -> None:
        """Test initialization creates empty state when no file exists."""
        assert metadata_manager.sounds == {}
        assert metadata_manager.all_tags == set()

    def test_get_metadata_creates_default(self, metadata_manager: MetadataManager) -> None:
        """Test get_metadata creates default metadata for unknown sounds."""
        meta = metadata_manager.get_metadata("new_sound")
        assert meta.tags == []
        assert meta.volume == 1.0
        assert "new_sound" in metadata_manager.sounds

    def test_add_tag(self, metadata_manager: MetadataManager) -> None:
        """Test adding tags to a sound."""
        assert metadata_manager.add_tag("airhorn", "meme") is True
        assert metadata_manager.add_tag("airhorn", "loud") is True

        meta = metadata_manager.get_metadata("airhorn")
        assert "meme" in meta.tags
        assert "loud" in meta.tags
        assert "meme" in metadata_manager.all_tags
        assert "loud" in metadata_manager.all_tags

    def test_add_duplicate_tag_returns_false(self, metadata_manager: MetadataManager) -> None:
        """Test adding duplicate tag returns False."""
        metadata_manager.add_tag("airhorn", "meme")
        assert metadata_manager.add_tag("airhorn", "meme") is False

    def test_add_tag_normalizes_case(self, metadata_manager: MetadataManager) -> None:
        """Test tags are normalized to lowercase."""
        metadata_manager.add_tag("airhorn", "MEME")
        meta = metadata_manager.get_metadata("airhorn")
        assert "meme" in meta.tags

    def test_remove_tag(self, metadata_manager: MetadataManager) -> None:
        """Test removing tags from a sound."""
        metadata_manager.add_tag("airhorn", "meme")
        metadata_manager.add_tag("airhorn", "loud")

        assert metadata_manager.remove_tag("airhorn", "meme") is True

        meta = metadata_manager.get_metadata("airhorn")
        assert "meme" not in meta.tags
        assert "loud" in meta.tags

    def test_remove_nonexistent_tag_returns_false(self, metadata_manager: MetadataManager) -> None:
        """Test removing nonexistent tag returns False."""
        assert metadata_manager.remove_tag("airhorn", "nonexistent") is False

    def test_get_sounds_by_tag(self, metadata_manager: MetadataManager) -> None:
        """Test filtering sounds by tag."""
        metadata_manager.add_tag("airhorn", "meme")
        metadata_manager.add_tag("rickroll", "meme")
        metadata_manager.add_tag("explosion", "effect")

        meme_sounds = metadata_manager.get_sounds_by_tag("meme")
        assert "airhorn" in meme_sounds
        assert "rickroll" in meme_sounds
        assert "explosion" not in meme_sounds

    def test_get_sounds_by_tags_or_logic(self, metadata_manager: MetadataManager) -> None:
        """Test filtering sounds by multiple tags (OR logic)."""
        metadata_manager.add_tag("airhorn", "meme")
        metadata_manager.add_tag("explosion", "effect")
        metadata_manager.add_tag("music", "calm")

        sounds = metadata_manager.get_sounds_by_tags(["meme", "effect"])
        assert "airhorn" in sounds
        assert "explosion" in sounds
        assert "music" not in sounds

    def test_set_favorite(self, metadata_manager: MetadataManager) -> None:
        """Test setting favorite status."""
        metadata_manager.set_favorite("airhorn", is_favorite=True)
        assert metadata_manager.get_metadata("airhorn").favorite is True

        metadata_manager.set_favorite("airhorn", is_favorite=False)
        assert metadata_manager.get_metadata("airhorn").favorite is False

    def test_toggle_favorite(self, metadata_manager: MetadataManager) -> None:
        """Test toggling favorite status."""
        assert metadata_manager.toggle_favorite("airhorn") is True
        assert metadata_manager.toggle_favorite("airhorn") is False
        assert metadata_manager.toggle_favorite("airhorn") is True

    def test_get_favorites(self, metadata_manager: MetadataManager) -> None:
        """Test getting favorite sounds."""
        metadata_manager.set_favorite("airhorn", is_favorite=True)
        metadata_manager.set_favorite("rickroll", is_favorite=True)
        metadata_manager.set_favorite("explosion", is_favorite=False)

        favorites = metadata_manager.get_favorites()
        assert "airhorn" in favorites
        assert "rickroll" in favorites
        assert "explosion" not in favorites

    def test_set_volume(self, metadata_manager: MetadataManager) -> None:
        """Test setting per-sound volume."""
        metadata_manager.set_volume("airhorn", 0.5)
        assert metadata_manager.get_metadata("airhorn").volume == 0.5

    def test_set_volume_clamped(self, metadata_manager: MetadataManager) -> None:
        """Test volume is clamped to valid range."""
        metadata_manager.set_volume("airhorn", 3.0)
        assert metadata_manager.get_metadata("airhorn").volume == 2.0

        metadata_manager.set_volume("airhorn", -1.0)
        assert metadata_manager.get_metadata("airhorn").volume == 0.0

    def test_record_play(self, metadata_manager: MetadataManager) -> None:
        """Test recording play events."""
        metadata_manager.record_play("airhorn")
        metadata_manager.record_play("airhorn")

        meta = metadata_manager.get_metadata("airhorn")
        assert meta.play_count == 2
        assert meta.last_played is not None

    def test_get_all_tags_with_counts(self, metadata_manager: MetadataManager) -> None:
        """Test getting all tags with their counts."""
        metadata_manager.add_tag("airhorn", "meme")
        metadata_manager.add_tag("rickroll", "meme")
        metadata_manager.add_tag("airhorn", "loud")

        counts = metadata_manager.get_all_tags_with_counts()
        assert counts["meme"] == 2
        assert counts["loud"] == 1

    def test_save_and_load(self, temp_metadata_file: Path) -> None:
        """Test saving and loading metadata."""
        # Create and populate manager
        manager1 = MetadataManager(metadata_file=temp_metadata_file)
        manager1.add_tag("airhorn", "meme")
        manager1.set_favorite("airhorn", is_favorite=True)
        manager1.set_volume("airhorn", 0.8)
        manager1.record_play("airhorn")

        # Create new manager to load from file
        manager2 = MetadataManager(metadata_file=temp_metadata_file)

        meta = manager2.get_metadata("airhorn")
        assert "meme" in meta.tags
        assert meta.favorite is True
        assert meta.volume == 0.8
        assert meta.play_count == 1

    def test_load_corrupted_file(self, temp_metadata_file: Path) -> None:
        """Test loading corrupted metadata file."""
        temp_metadata_file.parent.mkdir(parents=True, exist_ok=True)
        temp_metadata_file.write_text("invalid json {{{", encoding="utf-8")

        # Should not raise, just start fresh
        manager = MetadataManager(metadata_file=temp_metadata_file)
        assert manager.sounds == {}

    def test_cleanup_unused_tags(self, metadata_manager: MetadataManager) -> None:
        """Test cleanup of unused tags."""
        metadata_manager.add_tag("airhorn", "meme")
        metadata_manager.all_tags.add("unused_tag")

        removed = metadata_manager.cleanup_unused_tags()
        assert removed == 1
        assert "unused_tag" not in metadata_manager.all_tags
        assert "meme" in metadata_manager.all_tags
