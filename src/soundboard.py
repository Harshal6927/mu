# Copyright (c) 2025. All rights reserved.
"""Soundboard with hotkey bindings for playing audio files."""

import random
from pathlib import Path

from pynput import keyboard
from rich.console import Console
from rich.table import Table

from src.audio_manager import AudioManager
from src.hotkey_manager import HotkeyManager
from src.logging_config import get_logger
from src.metadata import MetadataManager
from src.profile_manager import ProfileManager
from src.sounds_directories import SoundsDirectoryManager
from src.validators import SUPPORTED_FORMATS, validate_audio_file_safe

logger = get_logger(__name__)


class Soundboard:
    """Manages sound files and hotkey bindings."""

    def __init__(
        self,
        audio_manager: AudioManager,
        sounds_dir: Path | None = None,
        console: Console | None = None,
        metadata_manager: MetadataManager | None = None,
        hotkey_manager: HotkeyManager | None = None,
        sounds_dirs: list[Path] | None = None,
    ) -> None:
        """Initialize the Soundboard.

        Args:
            audio_manager: The audio manager instance for playback
            sounds_dir: Primary directory containing sound files (legacy, use sounds_dirs)
            console: Rich console for output (creates new if None)
            metadata_manager: MetadataManager instance (creates new if None)
            hotkey_manager: HotkeyManager instance (creates new if None)
            sounds_dirs: List of directories to scan for sounds (preferred)

        """
        self.audio_manager = audio_manager
        self.console = console or Console()
        self.metadata = metadata_manager or MetadataManager()
        self.hotkey_manager = hotkey_manager or HotkeyManager()
        self.sounds: dict[str, Path] = {}
        self.sound_sources: dict[str, Path] = {}  # Track which directory each sound came from
        self.hotkeys: dict[str, str] = {}
        self.listener: keyboard.GlobalHotKeys | None = None
        self.invalid_files: list[tuple[Path, str]] = []  # Track invalid files

        # Set up sounds directories
        if sounds_dirs:
            self.sounds_dirs = sounds_dirs
            self.sounds_dir = sounds_dirs[0] if sounds_dirs else Path.cwd() / "sounds"
        elif sounds_dir:
            self.sounds_dirs = [sounds_dir]
            self.sounds_dir = sounds_dir
        else:
            self.sounds_dirs = [Path.cwd() / "sounds"]
            self.sounds_dir = Path.cwd() / "sounds"

        logger.debug(f"Soundboard initialized with sounds_dirs: {self.sounds_dirs}")

        # Scan for audio files
        self._scan_sounds()

    def _scan_sounds(self) -> None:
        """Scan the sounds directories for audio files with validation."""
        self.invalid_files = []
        self.sounds = {}
        self.sound_sources = {}

        if len(self.sounds_dirs) > 1:
            # Use SoundsDirectoryManager for multiple directories
            dir_manager = SoundsDirectoryManager(self.sounds_dirs)
            all_sounds = dir_manager.scan_all()

            for sound_name, (source_dir, audio_file) in all_sounds.items():
                # Validate the audio file
                file_info = validate_audio_file_safe(audio_file)

                if file_info.is_valid:
                    self.sounds[sound_name] = audio_file
                    self.sound_sources[sound_name] = source_dir
                    logger.debug(f"Found valid sound: {sound_name} from {source_dir}")
                else:
                    self.invalid_files.append((audio_file, file_info.error or "Unknown error"))
                    logger.warning(f"Invalid audio file: {audio_file} - {file_info.error}")
        else:
            # Single directory - original behavior
            sounds_dir = self.sounds_dirs[0] if self.sounds_dirs else self.sounds_dir
            if not sounds_dir.exists():
                logger.warning(f"Sounds directory not found: {sounds_dir}")
                self.console.print(
                    f"[yellow]⚠[/yellow] Sounds directory not found: {sounds_dir}",
                )
                return

            supported_extensions = list(SUPPORTED_FORMATS)

            for audio_file in sounds_dir.rglob("*"):
                if audio_file.suffix.lower() in supported_extensions:
                    # Validate the audio file
                    file_info = validate_audio_file_safe(audio_file)

                    if file_info.is_valid:
                        sound_name = audio_file.stem
                        self.sounds[sound_name] = audio_file
                        self.sound_sources[sound_name] = sounds_dir
                        logger.debug(f"Found valid sound: {sound_name}")
                    else:
                        self.invalid_files.append((audio_file, file_info.error or "Unknown error"))
                        logger.warning(f"Invalid audio file: {audio_file} - {file_info.error}")

        if self.sounds:
            logger.info(f"Found {len(self.sounds)} valid audio files")
            self.console.print(
                f"\n[green]✓[/green] Found [bold]{len(self.sounds)}[/bold] audio files",
            )

            # Report invalid files if any
            if self.invalid_files:
                self.console.print(
                    f"[yellow]⚠[/yellow] {len(self.invalid_files)} file(s) could not be loaded",
                )
                self.console.print("[dim]Run 'muc validate' for details[/dim]")
        else:
            dirs_str = ", ".join(str(d) for d in self.sounds_dirs)
            logger.warning(f"No audio files found in {dirs_str}")
            self.console.print(
                f"\n[yellow]⚠[/yellow] No audio files found in {dirs_str}",
            )
            self.console.print(
                f"[dim]Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}[/dim]",
            )

    def setup_default_hotkeys(self) -> None:
        """Set up default hotkey bindings for the first 10 sounds."""
        # Function keys F1-F10
        function_keys = [f"<f{i}>" for i in range(1, 11)]

        sound_names = sorted(self.sounds.keys())

        for idx, sound_name in enumerate(sound_names[:10]):
            self.hotkeys[function_keys[idx]] = sound_name

    def setup_hotkeys(self, *, mode: str | None = None) -> None:
        """Set up hotkeys based on configuration mode.

        Args:
            mode: Hotkey mode ("default", "custom", "merged"). Uses profile if None.

        """
        pm = ProfileManager()
        profile = pm.get_active_profile()
        mode = mode or profile.hotkey_mode

        if mode == "default":
            self.setup_default_hotkeys()
        elif mode == "custom":
            self.hotkeys = self.hotkey_manager.get_all_bindings()
        else:  # "merged"
            self.setup_default_hotkeys()
            # Custom hotkeys override defaults
            self.hotkeys.update(self.hotkey_manager.get_all_bindings())

    def set_hotkey(self, key: str, sound_name: str) -> bool:
        """Bind a hotkey to a sound.

        Args:
            key: Hotkey string (e.g., '<f1>', '<ctrl>+<alt>+a')
            sound_name: Name of the sound to play

        Returns:
            True if binding was successful

        """
        if sound_name not in self.sounds:
            self.console.print(f"[red]✗[/red] Sound '{sound_name}' not found.")
            return False

        self.hotkeys[key] = sound_name
        self.console.print(f"[green]✓[/green] Bound {key} to {sound_name}")
        return True

    def _create_hotkey_handler(self, sound_name: str):  # noqa: ANN202
        """Create a handler function for a specific sound.

        Args:
            sound_name: Name of the sound to play

        Returns:
            Handler function that plays the specified sound

        """

        def handler() -> None:
            audio_file = self.sounds.get(sound_name)
            if audio_file:
                # Get per-sound volume from metadata
                meta = self.metadata.get_metadata(sound_name)
                self.audio_manager.play_audio(audio_file, sound_volume=meta.volume)
                # Record play
                self.metadata.record_play(sound_name)

        return handler

    def start_listening(self) -> None:
        """Start listening for hotkeys."""
        if not self.hotkeys:
            logger.warning("No hotkeys configured")
            self.console.print(
                "[yellow]⚠[/yellow] No hotkeys configured. Use setup_default_hotkeys() first.",
            )
            return

        # Create handler mapping
        handlers = {}
        for key, sound_name in self.hotkeys.items():
            handlers[key] = self._create_hotkey_handler(sound_name)

        # Stop existing listener if any
        self.stop_listening()

        try:
            self.listener = keyboard.GlobalHotKeys(handlers)
            self.listener.start()
            logger.info("Hotkey listener started")
        except (OSError, RuntimeError) as e:
            logger.exception("Failed to start hotkey listener")
            self.console.print(f"[red]Error:[/red] {e}")

    def stop_listening(self) -> None:
        """Stop listening for hotkeys."""
        if self.listener:
            self.listener.stop()
            self.listener = None
            logger.debug("Hotkey listener stopped")

    def play_sound(self, sound_name: str, *, blocking: bool = False) -> bool:
        """Manually play a sound by name.

        Args:
            sound_name: Name of the sound to play
            blocking: If True, wait for playback to finish

        Returns:
            True if playback started successfully

        """
        audio_file = self.sounds.get(sound_name)
        if audio_file:
            logger.debug(f"Playing sound: {sound_name}")
            # Get per-sound volume from metadata
            meta = self.metadata.get_metadata(sound_name)
            result = self.audio_manager.play_audio(
                audio_file,
                blocking=blocking,
                sound_volume=meta.volume,
            )
            if result:
                # Record play
                self.metadata.record_play(sound_name)
            return result
        logger.warning(f"Sound not found: {sound_name}")
        self.console.print(f"[red]✗[/red] Sound '{sound_name}' not found.")
        return False

    def play_all_sounds(self, *, shuffle: bool = True) -> None:
        """Play all sounds in random or sequential order.

        Args:
            shuffle: If True, play sounds in random order. Default is True.

        Raises:
            KeyboardInterrupt: When user presses Ctrl+C to stop playback.

        """
        if not self.sounds:
            self.console.print("[yellow]⚠[/yellow] No sounds to play.")
            return

        sound_names = list(self.sounds.keys())
        if shuffle:
            random.shuffle(sound_names)
        else:
            sound_names = sorted(sound_names)

        total = len(sound_names)
        mode = "randomly" if shuffle else "sequentially"

        self.console.print(f"\n[bold cyan]Playing {total} sounds {mode}...[/bold cyan]")
        self.console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        try:
            for idx, sound_name in enumerate(sound_names, 1):
                self.console.print(f"[cyan][{idx}/{total}][/cyan] ", end="")
                self.play_sound(sound_name, blocking=True)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⏸[/yellow] Playback interrupted.")
            self.stop_sound()
            raise

    def list_sounds(self) -> None:
        """Print all available sounds in a formatted table."""
        if not self.sounds:
            self.console.print("[yellow]No sounds available.[/yellow]")
            return

        table = Table(
            title="Available Sounds",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Sound Name", style="white")
        table.add_column("Hotkey", style="green", justify="center")

        for idx, name in enumerate(sorted(self.sounds.keys()), 1):
            hotkey = next((k for k, v in self.hotkeys.items() if v == name), None)
            hotkey_display = hotkey.upper() if hotkey else "-"
            table.add_row(str(idx), name, hotkey_display)

        self.console.print(table)

    def list_hotkeys(self) -> None:
        """Print all configured hotkey bindings."""
        if not self.hotkeys:
            self.console.print("[yellow]No hotkeys configured.[/yellow]")
            return

        table = Table(
            title="Hotkey Bindings",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Hotkey", style="green", justify="center")
        table.add_column("Sound Name", style="white")

        for key, sound in sorted(self.hotkeys.items()):
            table.add_row(key.upper(), sound)

        self.console.print(table)

    def stop_sound(self) -> None:
        """Stop currently playing audio."""
        self.audio_manager.stop_audio()
