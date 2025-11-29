# Copyright (c) 2025. All rights reserved.
"""Tests for sounds directories manager module."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from rich.console import Console

from src.sounds_directories import SoundsDirectoryManager


class TestSoundsDirectoryManager:
    """Test the SoundsDirectoryManager class."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path]:
        """Create a temporary directory.

        Yields:
            Path: Temporary directory path.

        """
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def console(self) -> Console:
        """Create a console for testing.

        Returns:
            Console: Console instance for testing.

        """
        return Console(force_terminal=True, record=True)

    def test_initialization_empty(self) -> None:
        """Test initialization with no directories."""
        manager = SoundsDirectoryManager()
        assert manager.directories == []

    def test_initialization_with_directories(self, temp_dir: Path) -> None:
        """Test initialization with directories."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        manager = SoundsDirectoryManager([dir1, dir2])
        assert len(manager.directories) == 2
        assert dir1.resolve() in manager.directories
        assert dir2.resolve() in manager.directories

    def test_add_directory(self, temp_dir: Path) -> None:
        """Test adding a directory."""
        manager = SoundsDirectoryManager()
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()

        assert manager.add_directory(sounds_dir)
        assert sounds_dir.resolve() in manager.directories

    def test_add_directory_creates_if_not_exists(self, temp_dir: Path) -> None:
        """Test that add_directory creates the directory if it doesn't exist."""
        manager = SoundsDirectoryManager()
        sounds_dir = temp_dir / "new_sounds"

        assert not sounds_dir.exists()
        assert manager.add_directory(sounds_dir)
        assert sounds_dir.exists()

    def test_add_directory_duplicate_returns_false(self, temp_dir: Path) -> None:
        """Test that adding a duplicate directory returns False."""
        manager = SoundsDirectoryManager()
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()

        assert manager.add_directory(sounds_dir)
        assert not manager.add_directory(sounds_dir)

    def test_remove_directory(self, temp_dir: Path) -> None:
        """Test removing a directory."""
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()

        manager = SoundsDirectoryManager([sounds_dir])
        assert manager.remove_directory(sounds_dir)
        assert sounds_dir.resolve() not in manager.directories

    def test_remove_directory_not_found(self, temp_dir: Path) -> None:
        """Test removing a directory that's not in the list."""
        manager = SoundsDirectoryManager()
        sounds_dir = temp_dir / "sounds"

        assert not manager.remove_directory(sounds_dir)

    def test_scan_all_single_directory(self, temp_dir: Path) -> None:
        """Test scanning a single directory."""
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()

        # Create test files
        (sounds_dir / "sound1.wav").touch()
        (sounds_dir / "sound2.mp3").touch()
        (sounds_dir / "readme.txt").touch()  # Should be ignored

        manager = SoundsDirectoryManager([sounds_dir])
        sounds = manager.scan_all()

        assert "sound1" in sounds
        assert "sound2" in sounds
        assert "readme" not in sounds
        assert len(sounds) == 2

    def test_scan_all_multiple_directories(self, temp_dir: Path) -> None:
        """Test scanning multiple directories."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "sound1.wav").touch()
        (dir2 / "sound2.mp3").touch()

        manager = SoundsDirectoryManager([dir1, dir2])
        sounds = manager.scan_all()

        assert "sound1" in sounds
        assert "sound2" in sounds
        assert len(sounds) == 2

    def test_scan_all_later_directory_overrides(self, temp_dir: Path) -> None:
        """Test that later directories override earlier ones for same name."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        # Same name in both directories
        file1 = dir1 / "sound.wav"
        file2 = dir2 / "sound.mp3"
        file1.touch()
        file2.touch()

        manager = SoundsDirectoryManager([dir1, dir2])
        sounds = manager.scan_all()

        assert "sound" in sounds
        source_dir, file_path = sounds["sound"]
        assert source_dir == dir2.resolve()
        assert file_path == file2

    def test_scan_all_ignores_missing_directories(self, temp_dir: Path) -> None:
        """Test that scan_all ignores directories that don't exist."""
        existing = temp_dir / "existing"
        missing = temp_dir / "missing"
        existing.mkdir()

        (existing / "sound.wav").touch()

        manager = SoundsDirectoryManager([existing, missing])
        sounds = manager.scan_all()

        assert "sound" in sounds
        assert len(sounds) == 1

    def test_scan_all_recursive(self, temp_dir: Path) -> None:
        """Test that scan_all finds files in subdirectories."""
        sounds_dir = temp_dir / "sounds"
        subdir = sounds_dir / "subdir"
        sounds_dir.mkdir()
        subdir.mkdir()

        (sounds_dir / "sound1.wav").touch()
        (subdir / "sound2.wav").touch()

        manager = SoundsDirectoryManager([sounds_dir])
        sounds = manager.scan_all()

        assert "sound1" in sounds
        assert "sound2" in sounds

    def test_scan_directory(self, temp_dir: Path) -> None:
        """Test scanning a single directory without adding to manager."""
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()
        (sounds_dir / "sound.wav").touch()

        manager = SoundsDirectoryManager()
        sounds = manager.scan_directory(sounds_dir)

        assert "sound" in sounds
        assert len(manager.directories) == 0  # Not added to manager

    def test_get_sound_counts(self, temp_dir: Path) -> None:
        """Test getting sound counts per directory."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "a.wav").touch()
        (dir1 / "b.wav").touch()
        (dir2 / "c.wav").touch()

        manager = SoundsDirectoryManager([dir1, dir2])
        counts = manager.get_sound_counts()

        assert counts[dir1.resolve()] == 2
        assert counts[dir2.resolve()] == 1

    def test_get_directories_as_strings(self, temp_dir: Path) -> None:
        """Test getting directories as string list."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        manager = SoundsDirectoryManager([dir1, dir2])
        strings = manager.get_directories_as_strings()

        assert len(strings) == 2
        assert all(isinstance(s, str) for s in strings)

    def test_from_strings(self, temp_dir: Path) -> None:
        """Test creating manager from string list."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        manager = SoundsDirectoryManager.from_strings([str(dir1), str(dir2)])

        assert len(manager.directories) == 2

    def test_find_sound(self, temp_dir: Path) -> None:
        """Test finding a specific sound."""
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()
        sound_file = sounds_dir / "target.wav"
        sound_file.touch()

        manager = SoundsDirectoryManager([sounds_dir])
        result = manager.find_sound("target")

        assert result is not None
        _source_dir, file_path = result
        assert file_path == sound_file

    def test_find_sound_not_found(self, temp_dir: Path) -> None:
        """Test finding a sound that doesn't exist."""
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()

        manager = SoundsDirectoryManager([sounds_dir])
        result = manager.find_sound("nonexistent")

        assert result is None

    def test_find_sound_returns_last_match(self, temp_dir: Path) -> None:
        """Test that find_sound returns the last match (override behavior)."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        file1 = dir1 / "sound.wav"
        file2 = dir2 / "sound.mp3"
        file1.touch()
        file2.touch()

        manager = SoundsDirectoryManager([dir1, dir2])
        result = manager.find_sound("sound")

        assert result is not None
        source_dir, _file_path = result
        assert source_dir == dir2.resolve()

    def test_get_conflicts(self, temp_dir: Path) -> None:
        """Test getting sounds with name conflicts."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        # Conflict
        (dir1 / "conflict.wav").touch()
        (dir2 / "conflict.mp3").touch()
        # No conflict
        (dir1 / "unique.wav").touch()

        manager = SoundsDirectoryManager([dir1, dir2])
        conflicts = manager.get_conflicts()

        assert "conflict" in conflicts
        assert "unique" not in conflicts
        assert len(conflicts["conflict"]) == 2

    def test_get_conflicts_no_conflicts(self, temp_dir: Path) -> None:
        """Test get_conflicts when there are no conflicts."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "sound1.wav").touch()
        (dir2 / "sound2.wav").touch()

        manager = SoundsDirectoryManager([dir1, dir2])
        conflicts = manager.get_conflicts()

        assert len(conflicts) == 0

    def test_list_directories(self, temp_dir: Path, console: Console) -> None:
        """Test list_directories outputs a table."""
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()
        (sounds_dir / "sound.wav").touch()

        manager = SoundsDirectoryManager([sounds_dir])
        manager.list_directories(console)

        output = console.export_text()
        assert "Sounds Directories" in output

    def test_list_directories_empty(self, console: Console) -> None:
        """Test list_directories with no directories."""
        manager = SoundsDirectoryManager()
        manager.list_directories(console)

        output = console.export_text()
        assert "No sounds directories configured" in output

    def test_show_conflicts(self, temp_dir: Path, console: Console) -> None:
        """Test show_conflicts outputs conflict information."""
        dir1 = temp_dir / "sounds1"
        dir2 = temp_dir / "sounds2"
        dir1.mkdir()
        dir2.mkdir()

        (dir1 / "conflict.wav").touch()
        (dir2 / "conflict.mp3").touch()

        manager = SoundsDirectoryManager([dir1, dir2])
        manager.show_conflicts(console)

        output = console.export_text()
        assert "conflict" in output.lower()

    def test_show_conflicts_no_conflicts(self, temp_dir: Path, console: Console) -> None:
        """Test show_conflicts when there are no conflicts."""
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()
        (sounds_dir / "unique.wav").touch()

        manager = SoundsDirectoryManager([sounds_dir])
        manager.show_conflicts(console)

        output = console.export_text()
        assert "No sound name conflicts found" in output

    def test_supported_formats(self, temp_dir: Path) -> None:
        """Test that all supported formats are detected."""
        sounds_dir = temp_dir / "sounds"
        sounds_dir.mkdir()

        # Create files with all supported extensions
        (sounds_dir / "a.wav").touch()
        (sounds_dir / "b.mp3").touch()
        (sounds_dir / "c.ogg").touch()
        (sounds_dir / "d.flac").touch()
        (sounds_dir / "e.m4a").touch()

        manager = SoundsDirectoryManager([sounds_dir])
        sounds = manager.scan_all()

        assert len(sounds) == 5
        assert "a" in sounds
        assert "b" in sounds
        assert "c" in sounds
        assert "d" in sounds
        assert "e" in sounds
