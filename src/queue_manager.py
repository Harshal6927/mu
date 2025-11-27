# Copyright (c) 2025. All rights reserved.
"""Sound queue and playlist management for MUC Soundboard."""

import json
import random
from collections import deque
from pathlib import Path
from threading import Lock

from .logging_config import get_logger

logger = get_logger(__name__)


class QueueManager:
    """Manages sound playback queue and playlists."""

    def __init__(self, playlists_file: Path | None = None) -> None:
        """Initialize QueueManager.

        Args:
            playlists_file: Path to playlists JSON file (default: ~/.muc/playlists.json)

        """
        self.playlists_file = playlists_file or (Path.home() / ".muc" / "playlists.json")
        self.queue: deque[str] = deque()
        self.playlists: dict[str, list[str]] = {}
        self._lock = Lock()
        self._load_playlists()

    def _load_playlists(self) -> None:
        """Load playlists from file."""
        logger.debug(f"Loading playlists from {self.playlists_file}")

        if not self.playlists_file.exists():
            logger.info("No playlists file found, starting fresh")
            return

        try:
            with self.playlists_file.open(encoding="utf-8") as f:
                self.playlists = json.load(f)
            logger.info(f"Loaded {len(self.playlists)} playlist(s)")
        except json.JSONDecodeError:
            logger.exception("Playlists file corrupted, starting fresh")
        except OSError:
            logger.exception("Cannot read playlists file")

    def _save_playlists(self) -> None:
        """Save playlists to file."""
        logger.debug("Saving playlists")

        self.playlists_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self.playlists_file.open("w", encoding="utf-8") as f:
                json.dump(self.playlists, f, indent=2)
            logger.debug("Playlists saved successfully")
        except OSError:
            logger.exception("Failed to save playlists")

    def add(self, *sound_names: str) -> int:
        """Add sounds to the queue.

        Args:
            sound_names: Sound names to add

        Returns:
            Number of sounds added

        """
        with self._lock:
            self.queue.extend(sound_names)
            logger.debug(f"Added {len(sound_names)} sound(s) to queue")
            return len(sound_names)

    def clear(self) -> int:
        """Clear the queue.

        Returns:
            Number of sounds removed

        """
        with self._lock:
            count = len(self.queue)
            self.queue.clear()
            logger.debug(f"Cleared {count} sound(s) from queue")
            return count

    def next(self) -> str | None:
        """Get and remove the next sound from queue.

        Returns:
            Next sound name, or None if queue is empty

        """
        with self._lock:
            if self.queue:
                sound = self.queue.popleft()
                logger.debug(f"Dequeued: {sound}")
                return sound
            return None

    def peek(self) -> list[str]:
        """Get queue contents without modifying.

        Returns:
            List of sound names in queue order

        """
        with self._lock:
            return list(self.queue)

    def size(self) -> int:
        """Get the number of sounds in the queue.

        Returns:
            Queue size

        """
        with self._lock:
            return len(self.queue)

    def is_empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if queue has no sounds

        """
        with self._lock:
            return len(self.queue) == 0

    def shuffle(self) -> None:
        """Shuffle the queue."""
        with self._lock:
            items = list(self.queue)
            random.shuffle(items)
            self.queue = deque(items)
            logger.debug("Queue shuffled")

    def remove(self, sound_name: str) -> int:
        """Remove all occurrences of a sound from queue.

        Args:
            sound_name: Sound name to remove

        Returns:
            Number of occurrences removed

        """
        with self._lock:
            original_len = len(self.queue)
            self.queue = deque(s for s in self.queue if s != sound_name)
            removed = original_len - len(self.queue)
            if removed:
                logger.debug(f"Removed {removed} occurrence(s) of '{sound_name}' from queue")
            return removed

    def save_playlist(self, name: str) -> bool:
        """Save current queue as a named playlist.

        Args:
            name: Playlist name

        Returns:
            True if saved successfully

        """
        with self._lock:
            if not self.queue:
                logger.warning("Cannot save empty queue as playlist")
                return False
            self.playlists[name] = list(self.queue)
        self._save_playlists()
        logger.info(f"Saved playlist '{name}' with {len(self.queue)} sound(s)")
        return True

    def load_playlist(self, name: str, *, append: bool = False) -> bool:
        """Load a playlist into the queue.

        Args:
            name: Playlist name
            append: If True, append to queue; if False, replace queue

        Returns:
            True if playlist was found and loaded

        """
        if name not in self.playlists:
            logger.warning(f"Playlist '{name}' not found")
            return False

        with self._lock:
            if append:
                self.queue.extend(self.playlists[name])
            else:
                self.queue = deque(self.playlists[name])

        logger.info(f"Loaded playlist '{name}' ({'appended' if append else 'replaced'})")
        return True

    def delete_playlist(self, name: str) -> bool:
        """Delete a saved playlist.

        Args:
            name: Playlist name

        Returns:
            True if playlist was found and deleted

        """
        if name in self.playlists:
            del self.playlists[name]
            self._save_playlists()
            logger.info(f"Deleted playlist '{name}'")
            return True
        return False

    def list_playlists(self) -> dict[str, int]:
        """Get all playlists with their sizes.

        Returns:
            Dictionary mapping playlist names to number of sounds

        """
        return {name: len(sounds) for name, sounds in self.playlists.items()}

    def get_playlist(self, name: str) -> list[str] | None:
        """Get the contents of a playlist.

        Args:
            name: Playlist name

        Returns:
            List of sound names, or None if not found

        """
        return self.playlists.get(name, None)

    def rename_playlist(self, old_name: str, new_name: str) -> bool:
        """Rename a playlist.

        Args:
            old_name: Current playlist name
            new_name: New playlist name

        Returns:
            True if renamed successfully

        """
        if old_name not in self.playlists:
            return False
        if new_name in self.playlists:
            logger.warning(f"Playlist '{new_name}' already exists")
            return False

        self.playlists[new_name] = self.playlists.pop(old_name)
        self._save_playlists()
        logger.info(f"Renamed playlist '{old_name}' to '{new_name}'")
        return True
