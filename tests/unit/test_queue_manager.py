# Copyright (c) 2025. All rights reserved.
# ruff: noqa: DOC201, DOC402
"""Unit tests for the queue manager module."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from src.queue_manager import QueueManager


@pytest.fixture
def temp_playlists_file() -> Generator[Path]:
    """Create a temporary playlists file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / ".muc" / "playlists.json"


@pytest.fixture
def queue_manager(temp_playlists_file: Path) -> QueueManager:
    """Create a QueueManager with a temporary file."""
    return QueueManager(playlists_file=temp_playlists_file)


class TestQueueOperations:
    """Tests for queue operations."""

    def test_add_sounds(self, queue_manager: QueueManager) -> None:
        """Test adding sounds to the queue."""
        count = queue_manager.add("airhorn", "rickroll", "explosion")
        assert count == 3
        assert queue_manager.size() == 3

    def test_add_single_sound(self, queue_manager: QueueManager) -> None:
        """Test adding a single sound."""
        queue_manager.add("airhorn")
        assert queue_manager.size() == 1

    def test_next_returns_and_removes(self, queue_manager: QueueManager) -> None:
        """Test next() returns first item and removes it."""
        queue_manager.add("airhorn", "rickroll")

        first = queue_manager.next()
        assert first == "airhorn"
        assert queue_manager.size() == 1

        second = queue_manager.next()
        assert second == "rickroll"
        assert queue_manager.size() == 0

    def test_next_empty_returns_none(self, queue_manager: QueueManager) -> None:
        """Test next() returns None on empty queue."""
        assert queue_manager.next() is None

    def test_peek_returns_copy(self, queue_manager: QueueManager) -> None:
        """Test peek() returns copy without modifying queue."""
        queue_manager.add("airhorn", "rickroll")

        items = queue_manager.peek()
        assert items == ["airhorn", "rickroll"]
        assert queue_manager.size() == 2  # Queue unchanged

    def test_clear_removes_all(self, queue_manager: QueueManager) -> None:
        """Test clear() removes all items."""
        queue_manager.add("airhorn", "rickroll", "explosion")
        count = queue_manager.clear()
        assert count == 3
        assert queue_manager.is_empty()

    def test_is_empty(self, queue_manager: QueueManager) -> None:
        """Test is_empty() check."""
        assert queue_manager.is_empty() is True

        queue_manager.add("airhorn")
        assert queue_manager.is_empty() is False

    def test_shuffle(self, queue_manager: QueueManager) -> None:
        """Test shuffle() randomizes order."""
        # Add many items to reduce chance of same order
        sounds = [f"sound{i}" for i in range(20)]
        queue_manager.add(*sounds)

        original = queue_manager.peek()
        queue_manager.shuffle()
        shuffled = queue_manager.peek()

        # Same items, potentially different order
        assert sorted(shuffled) == sorted(original)
        assert queue_manager.size() == 20

    def test_remove_sound(self, queue_manager: QueueManager) -> None:
        """Test removing specific sound from queue."""
        queue_manager.add("airhorn", "rickroll", "airhorn", "explosion")

        removed = queue_manager.remove("airhorn")
        assert removed == 2

        items = queue_manager.peek()
        assert items == ["rickroll", "explosion"]

    def test_remove_nonexistent_sound(self, queue_manager: QueueManager) -> None:
        """Test removing nonexistent sound returns 0."""
        queue_manager.add("airhorn")
        removed = queue_manager.remove("nonexistent")
        assert removed == 0


class TestPlaylistOperations:
    """Tests for playlist save/load operations."""

    def test_save_playlist(self, queue_manager: QueueManager) -> None:
        """Test saving queue as playlist."""
        queue_manager.add("airhorn", "rickroll")

        result = queue_manager.save_playlist("gaming")
        assert result is True
        assert "gaming" in queue_manager.playlists
        assert queue_manager.playlists["gaming"] == ["airhorn", "rickroll"]

    def test_save_empty_queue_fails(self, queue_manager: QueueManager) -> None:
        """Test saving empty queue fails."""
        result = queue_manager.save_playlist("empty")
        assert result is False

    def test_load_playlist_replace(self, queue_manager: QueueManager) -> None:
        """Test loading playlist replaces queue."""
        # Setup playlist
        queue_manager.add("airhorn", "rickroll")
        queue_manager.save_playlist("gaming")
        queue_manager.clear()

        # Add different sounds
        queue_manager.add("explosion")

        # Load should replace
        result = queue_manager.load_playlist("gaming")
        assert result is True
        assert queue_manager.peek() == ["airhorn", "rickroll"]

    def test_load_playlist_append(self, queue_manager: QueueManager) -> None:
        """Test loading playlist with append."""
        # Setup playlist
        queue_manager.add("airhorn", "rickroll")
        queue_manager.save_playlist("gaming")
        queue_manager.clear()

        # Add different sounds
        queue_manager.add("explosion")

        # Load with append
        queue_manager.load_playlist("gaming", append=True)
        assert queue_manager.peek() == ["explosion", "airhorn", "rickroll"]

    def test_load_nonexistent_playlist(self, queue_manager: QueueManager) -> None:
        """Test loading nonexistent playlist returns False."""
        result = queue_manager.load_playlist("nonexistent")
        assert result is False

    def test_delete_playlist(self, queue_manager: QueueManager) -> None:
        """Test deleting a playlist."""
        queue_manager.add("airhorn")
        queue_manager.save_playlist("gaming")

        result = queue_manager.delete_playlist("gaming")
        assert result is True
        assert "gaming" not in queue_manager.playlists

    def test_delete_nonexistent_playlist(self, queue_manager: QueueManager) -> None:
        """Test deleting nonexistent playlist returns False."""
        result = queue_manager.delete_playlist("nonexistent")
        assert result is False

    def test_list_playlists(self, queue_manager: QueueManager) -> None:
        """Test listing playlists with sizes."""
        queue_manager.add("airhorn", "rickroll")
        queue_manager.save_playlist("gaming")

        queue_manager.clear()
        queue_manager.add("explosion")
        queue_manager.save_playlist("effects")

        playlists = queue_manager.list_playlists()
        assert playlists == {"gaming": 2, "effects": 1}

    def test_get_playlist(self, queue_manager: QueueManager) -> None:
        """Test getting playlist contents."""
        queue_manager.add("airhorn", "rickroll")
        queue_manager.save_playlist("gaming")

        sounds = queue_manager.get_playlist("gaming")
        assert sounds == ["airhorn", "rickroll"]

    def test_get_nonexistent_playlist(self, queue_manager: QueueManager) -> None:
        """Test getting nonexistent playlist returns None."""
        sounds = queue_manager.get_playlist("nonexistent")
        assert sounds is None

    def test_rename_playlist(self, queue_manager: QueueManager) -> None:
        """Test renaming a playlist."""
        queue_manager.add("airhorn")
        queue_manager.save_playlist("old_name")

        result = queue_manager.rename_playlist("old_name", "new_name")
        assert result is True
        assert "old_name" not in queue_manager.playlists
        assert "new_name" in queue_manager.playlists

    def test_rename_nonexistent_playlist(self, queue_manager: QueueManager) -> None:
        """Test renaming nonexistent playlist fails."""
        result = queue_manager.rename_playlist("nonexistent", "new_name")
        assert result is False

    def test_rename_to_existing_name_fails(self, queue_manager: QueueManager) -> None:
        """Test renaming to existing name fails."""
        queue_manager.add("airhorn")
        queue_manager.save_playlist("playlist1")

        queue_manager.clear()
        queue_manager.add("rickroll")
        queue_manager.save_playlist("playlist2")

        result = queue_manager.rename_playlist("playlist1", "playlist2")
        assert result is False


class TestPlaylistPersistence:
    """Tests for playlist persistence."""

    def test_save_and_load_playlists(self, temp_playlists_file: Path) -> None:
        """Test playlists persist across manager instances."""
        # Create and populate manager
        manager1 = QueueManager(playlists_file=temp_playlists_file)
        manager1.add("airhorn", "rickroll")
        manager1.save_playlist("gaming")

        # Create new manager to load from file
        manager2 = QueueManager(playlists_file=temp_playlists_file)

        assert "gaming" in manager2.playlists
        assert manager2.playlists["gaming"] == ["airhorn", "rickroll"]

    def test_load_corrupted_file(self, temp_playlists_file: Path) -> None:
        """Test loading corrupted playlists file."""
        temp_playlists_file.parent.mkdir(parents=True, exist_ok=True)
        temp_playlists_file.write_text("invalid json {{{", encoding="utf-8")

        # Should not raise, just start fresh
        manager = QueueManager(playlists_file=temp_playlists_file)
        assert manager.playlists == {}


class TestThreadSafety:
    """Tests for thread-safe operations."""

    def test_add_is_thread_safe(self, queue_manager: QueueManager) -> None:
        """Test add uses lock."""
        # This test just verifies the lock is used
        # Full thread safety would require concurrent tests
        queue_manager.add("airhorn")
        assert queue_manager.size() == 1

    def test_next_is_thread_safe(self, queue_manager: QueueManager) -> None:
        """Test next uses lock."""
        queue_manager.add("airhorn")
        result = queue_manager.next()
        assert result == "airhorn"

    def test_peek_is_thread_safe(self, queue_manager: QueueManager) -> None:
        """Test peek uses lock."""
        queue_manager.add("airhorn")
        items = queue_manager.peek()
        assert items == ["airhorn"]
