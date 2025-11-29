# Copyright (c) 2025. All rights reserved.
"""Multiple sounds directory management for MUC Soundboard."""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from .logging_config import get_logger
from .validators import SUPPORTED_FORMATS

logger = get_logger(__name__)


class SoundsDirectoryManager:
    """Manages multiple sounds directories."""

    def __init__(self, directories: list[Path] | None = None) -> None:
        """Initialize SoundsDirectoryManager.

        Args:
            directories: List of sound directories to manage

        """
        self.directories: list[Path] = []
        if directories:
            for d in directories:
                self.directories.append(d.resolve())

    def add_directory(self, path: Path) -> bool:
        """Add a sounds directory.

        Args:
            path: Path to the sounds directory

        Returns:
            True if added, False if already exists

        """
        path = path.resolve()
        if path in self.directories:
            logger.debug(f"Directory already configured: {path}")
            return False
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created sounds directory: {path}")
        self.directories.append(path)
        logger.info(f"Added sounds directory: {path}")
        return True

    def remove_directory(self, path: Path) -> bool:
        """Remove a sounds directory.

        Args:
            path: Path to remove

        Returns:
            True if removed, False if not found

        """
        path = path.resolve()
        if path in self.directories:
            self.directories.remove(path)
            logger.info(f"Removed sounds directory: {path}")
            return True
        logger.debug(f"Directory not found: {path}")
        return False

    def scan_all(self) -> dict[str, tuple[Path, Path]]:
        """Scan all directories for sounds.

        Later directories take precedence for name conflicts.

        Returns:
            Dict mapping sound name to (source_dir, file_path)

        """
        sounds: dict[str, tuple[Path, Path]] = {}

        for directory in self.directories:
            if not directory.exists():
                logger.warning(f"Sounds directory not found: {directory}")
                continue

            for audio_file in directory.rglob("*"):
                if audio_file.suffix.lower() in SUPPORTED_FORMATS:
                    name = audio_file.stem
                    if name in sounds:
                        _, old_path = sounds[name]
                        logger.debug(
                            f"Sound '{name}' overridden: {old_path} -> {audio_file}",
                        )
                    sounds[name] = (directory, audio_file)

        logger.info(f"Found {len(sounds)} sounds across {len(self.directories)} directories")
        return sounds

    def scan_directory(self, directory: Path) -> dict[str, Path]:
        """Scan a single directory for sounds.

        Args:
            directory: Directory to scan

        Returns:
            Dict mapping sound name to file path

        """
        sounds: dict[str, Path] = {}
        directory = directory.resolve()

        if not directory.exists():
            return sounds

        for audio_file in directory.rglob("*"):
            if audio_file.suffix.lower() in SUPPORTED_FORMATS:
                name = audio_file.stem
                sounds[name] = audio_file

        return sounds

    def get_sound_counts(self) -> dict[Path, int]:
        """Get sound counts per directory.

        Returns:
            Dict mapping directory path to sound count

        """
        counts: dict[Path, int] = {}
        for directory in self.directories:
            if directory.exists():
                count = sum(1 for f in directory.rglob("*") if f.suffix.lower() in SUPPORTED_FORMATS)
                counts[directory] = count
            else:
                counts[directory] = 0
        return counts

    def list_directories(self, console: Console) -> None:
        """Display all configured directories in a table.

        Args:
            console: Rich console for output

        """
        table = Table(title="Sounds Directories", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Path", style="white")
        table.add_column("Sounds", justify="right")
        table.add_column("Status", justify="center")

        for idx, directory in enumerate(self.directories, 1):
            if directory.exists():
                count = sum(1 for f in directory.rglob("*") if f.suffix.lower() in SUPPORTED_FORMATS)
                status = "[green]OK[/green]"
            else:
                count = 0
                status = "[red]NOT FOUND[/red]"

            table.add_row(str(idx), str(directory), str(count), status)

        if not self.directories:
            console.print("[yellow]⚠[/yellow] No sounds directories configured")
        else:
            console.print(table)

    def get_directories_as_strings(self) -> list[str]:
        """Get directories as list of strings.

        Returns:
            List of directory paths as strings

        """
        return [str(d) for d in self.directories]

    @classmethod
    def from_strings(cls, dir_strings: list[str]) -> "SoundsDirectoryManager":
        """Create manager from list of path strings.

        Args:
            dir_strings: List of directory path strings

        Returns:
            SoundsDirectoryManager instance

        """
        return cls([Path(d) for d in dir_strings])

    def find_sound(self, name: str) -> tuple[Path, Path] | None:
        """Find a specific sound across all directories.

        Searches directories in order, returns the last match
        (matching the override behavior).

        Args:
            name: Sound name to find

        Returns:
            Tuple of (source_dir, file_path) if found, None otherwise

        """
        result: tuple[Path, Path] | None = None

        for directory in self.directories:
            if not directory.exists():
                continue

            for audio_file in directory.rglob("*"):
                if audio_file.suffix.lower() in SUPPORTED_FORMATS and audio_file.stem == name:
                    result = (directory, audio_file)
                    # Continue searching to get the last match

        return result

    def get_conflicts(self) -> dict[str, list[tuple[Path, Path]]]:
        """Find sounds with name conflicts across directories.

        Returns:
            Dict mapping sound name to list of (source_dir, file_path) tuples

        """
        all_sounds: dict[str, list[tuple[Path, Path]]] = {}

        for directory in self.directories:
            if not directory.exists():
                continue

            for audio_file in directory.rglob("*"):
                if audio_file.suffix.lower() in SUPPORTED_FORMATS:
                    name = audio_file.stem
                    if name not in all_sounds:
                        all_sounds[name] = []
                    all_sounds[name].append((directory, audio_file))

        # Return only sounds with conflicts (more than one source)
        return {name: sources for name, sources in all_sounds.items() if len(sources) > 1}

    def show_conflicts(self, console: Console) -> None:
        """Display any sound name conflicts.

        Args:
            console: Rich console for output

        """
        conflicts = self.get_conflicts()

        if not conflicts:
            console.print("[green]✓[/green] No sound name conflicts found")
            return

        console.print(f"\n[yellow]⚠[/yellow] Found {len(conflicts)} sound(s) with name conflicts:\n")

        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Sound Name", style="white")
        table.add_column("Sources", style="dim")
        table.add_column("Active", style="green")

        for name, sources in sorted(conflicts.items()):
            source_list = "\n".join(str(src) for src, _ in sources[:-1])
            active_source = str(sources[-1][0])  # Last directory wins
            table.add_row(name, source_list, active_source)

        console.print(table)
        console.print("\n[dim]Note: When names conflict, the sound from the last directory is used[/dim]")
