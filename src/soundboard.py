# Copyright (c) 2025. All rights reserved.
"""Soundboard with hotkey bindings for playing audio files."""

import random
from pathlib import Path

from pynput import keyboard
from rich.console import Console
from rich.table import Table

from .audio_manager import AudioManager
from .logging_config import get_logger
from .validators import SUPPORTED_FORMATS, validate_audio_file_safe

logger = get_logger(__name__)


class Soundboard:
    """Manages sound files and hotkey bindings."""

    def __init__(
        self,
        audio_manager: AudioManager,
        sounds_dir: Path,
        console: Console | None = None,
    ) -> None:
        """Initialize the Soundboard.

        Args:
            audio_manager: The audio manager instance for playback
            sounds_dir: Directory containing sound files
            console: Rich console for output (creates new if None)

        """
        self.audio_manager = audio_manager
        self.sounds_dir = Path(sounds_dir)
        self.console = console or Console()
        self.sounds: dict[str, Path] = {}
        self.hotkeys: dict[str, str] = {}
        self.listener: keyboard.GlobalHotKeys | None = None
        self.invalid_files: list[tuple[Path, str]] = []  # Track invalid files

        logger.debug(f"Soundboard initialized with sounds_dir: {self.sounds_dir}")

        # Scan for audio files
        self._scan_sounds()

    def _scan_sounds(self) -> None:
        """Scan the sounds directory for audio files with validation."""
        if not self.sounds_dir.exists():
            logger.warning(f"Sounds directory not found: {self.sounds_dir}")
            self.console.print(
                f"[yellow]⚠[/yellow] Sounds directory not found: {self.sounds_dir}",
            )
            return

        supported_extensions = list(SUPPORTED_FORMATS)
        self.invalid_files = []

        for audio_file in self.sounds_dir.rglob("*"):
            if audio_file.suffix.lower() in supported_extensions:
                # Validate the audio file
                file_info = validate_audio_file_safe(audio_file)

                if file_info.is_valid:
                    # Use filename without extension as the sound name
                    sound_name = audio_file.stem
                    self.sounds[sound_name] = audio_file
                    logger.debug(f"Found valid sound: {sound_name}")
                else:
                    # Track invalid files but don't crash
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
            logger.warning(f"No audio files found in {self.sounds_dir}")
            self.console.print(
                f"\n[yellow]⚠[/yellow] No audio files found in {self.sounds_dir}",
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
                self.audio_manager.play_audio(audio_file)

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
            return self.audio_manager.play_audio(audio_file, blocking=blocking)
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
