# Copyright (c) 2025. All rights reserved.
"""Audio device management and playback functionality."""

import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from rich.console import Console
from rich.table import Table

from .exceptions import (
    AudioFileCorruptedError,
    DeviceDisconnectedError,
    DeviceNoOutputError,
    DeviceNotFoundError,
)
from .logging_config import get_logger
from .validators import validate_device

logger = get_logger(__name__)


class AudioManager:
    """Manages audio devices and playback operations."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the AudioManager.

        Args:
            console: Rich console for output (creates new if None)

        """
        self.console = console or Console()
        self.current_stream = None
        self.output_device_id: int | None = None
        self.volume: float = 1.0
        logger.debug("AudioManager initialized")

    def list_devices(self):  # noqa: ANN201
        """List all available audio devices.

        Returns:
            Device list from sounddevice query.

        """
        return sd.query_devices()

    def find_virtual_cable(self) -> int | None:
        """Find VB-Cable or similar virtual audio device.

        Returns:
            The device ID if found, None otherwise.

        """
        devices = self.list_devices()
        keywords = ["cable", "virtual", "vb-audio", "voicemeeter"]

        for idx in range(len(devices)):
            device = sd.query_devices(idx)
            device_name = str(device["name"]).lower()  # pyright: ignore[reportArgumentType, reportCallIssue]
            if any(keyword in device_name for keyword in keywords) and device["max_output_channels"] > 0:  # pyright: ignore[reportArgumentType, reportCallIssue]
                return idx
        return None

    def print_devices(self) -> None:
        """Print all audio devices with their IDs in a formatted table."""
        table = Table(
            title="Available Audio Devices",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("ID", style="dim", width=4, justify="right")
        table.add_column("Device Name", style="white")
        table.add_column("Inputs", justify="center", width=8)
        table.add_column("Outputs", justify="center", width=8)
        table.add_column("Status", justify="center", width=10)

        devices = self.list_devices()
        for idx in range(len(devices)):
            device = sd.query_devices(idx)
            status = "[green]SELECTED[/green]" if self.output_device_id == idx else ""

            table.add_row(
                str(idx),
                str(device["name"]),  # pyright: ignore[reportArgumentType, reportCallIssue]
                str(device["max_input_channels"]),  # pyright: ignore[reportArgumentType, reportCallIssue]
                str(device["max_output_channels"]),  # pyright: ignore[reportArgumentType, reportCallIssue]
                status,
            )

        self.console.print(table)

    def set_output_device(self, device_id: int) -> bool:
        """Set the output device for audio playback.

        Args:
            device_id: ID of the device to set as output

        Returns:
            True if device was set successfully, False otherwise.

        """
        try:
            device_info = validate_device(device_id)
            self.output_device_id = device_id
            logger.info(f"Output device set to: {device_info.name} (ID: {device_id})")
        except DeviceNotFoundError as e:
            logger.warning(f"Device not found: {e}")
            self.console.print(f"[red]✗[/red] {e.message}")
            self.console.print(f"[dim]💡 {e.suggestion}[/dim]")
            return False
        except DeviceNoOutputError as e:
            logger.warning(f"Device has no output: {e}")
            self.console.print(f"[red]✗[/red] {e.message}")
            self.console.print(f"[dim]💡 {e.suggestion}[/dim]")
            return False
        else:
            self.console.print(
                f"[green]✓[/green] Output device set to: [bold]{device_info.name}[/bold]",
            )
            return True

    def set_volume(self, volume: float) -> None:
        """Set the playback volume level.

        Args:
            volume: Volume level from 0.0 (mute) to 1.0 (full volume)

        """
        self.volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
        percentage = int(self.volume * 100)
        logger.debug(f"Volume set to {percentage}%")
        self.console.print(f"[cyan]♪[/cyan] Volume set to {percentage}%")

    @staticmethod
    def _adjust_channels(data: np.ndarray, max_channels: int) -> np.ndarray:
        """Adjust audio channels to match the output device.

        Args:
            data: Audio data array
            max_channels: Target number of channels

        Returns:
            Adjusted audio data array

        """
        if data.shape[1] < max_channels:
            # Duplicate channels to fill as much as possible
            tile_count = max_channels // data.shape[1]
            data = np.tile(data, (1, tile_count))

            # If we still don't have enough channels (e.g. 2 -> 5), pad with silence
            current_channels = data.shape[1]
            if current_channels < max_channels:
                padding = np.zeros((data.shape[0], max_channels - current_channels))
                data = np.hstack((data, padding))

        elif data.shape[1] > max_channels:
            # Take only the channels we need
            data = data[:, :max_channels]

        return data

    def play_audio(self, audio_file: Path, *, blocking: bool = False) -> bool:
        """Play an audio file through the selected output device.

        Args:
            audio_file: Path to the audio file
            blocking: If True, wait for playback to finish

        Returns:
            True if playback started successfully, False otherwise.

        """
        if self.output_device_id is None:
            logger.warning("No output device selected")
            self.console.print(
                "[yellow]⚠[/yellow] No output device selected. Use 'muc setup' first.",
            )
            return False

        if not audio_file.exists():
            logger.warning(f"Audio file not found: {audio_file}")
            self.console.print(f"[red]✗[/red] Audio file not found: {audio_file}")
            return False

        # Verify device is still available before playback
        try:
            validate_device(self.output_device_id)
        except (DeviceNotFoundError, DeviceNoOutputError) as e:
            logger.exception("Device validation failed")
            self.console.print(f"[red]✗[/red] {e.message}")
            self.console.print(f"[dim]💡 {e.suggestion}[/dim]")
            return False

        try:
            # Stop any currently playing audio
            self.stop_audio()

            logger.debug(f"Loading audio file: {audio_file}")

            # Load and play the audio file
            data, samplerate = sf.read(str(audio_file))  # pyright: ignore[reportGeneralTypeIssues]

            # Ensure data is in the correct format
            if len(data.shape) == 1:
                # Mono audio
                data = data.reshape(-1, 1)

            # Get device info to match channels
            device_info = sd.query_devices(self.output_device_id)
            max_channels = device_info["max_output_channels"]  # pyright: ignore[reportCallIssue, reportArgumentType]

            logger.debug(
                f"Audio info: duration={len(data) / samplerate:.2f}s, rate={samplerate}, channels={data.shape[1]}",
            )

            # Adjust channels if needed
            data = self._adjust_channels(data, max_channels)

            # Apply volume scaling
            data *= self.volume

            logger.debug(f"Starting playback to device {self.output_device_id}")
            sd.play(data, samplerate, device=self.output_device_id)

            if blocking:
                # Use polling loop instead of sd.wait() to allow KeyboardInterrupt
                while sd.get_stream() and sd.get_stream().active:
                    time.sleep(0.1)

        except sf.LibsndfileError as e:
            logger.exception("Failed to read audio file")
            error = AudioFileCorruptedError(
                f"Cannot read audio file: {audio_file.name}",
                details={"path": str(audio_file), "error": str(e)},
            )
            self.console.print(f"[red]✗[/red] {error.message}")
            self.console.print(f"[dim]💡 {error.suggestion}[/dim]")
            return False
        except sd.PortAudioError as e:
            # Device disconnection or error during playback
            if "device" in str(e).lower() or "stream" in str(e).lower():
                logger.exception("Device error during playback")
                error = DeviceDisconnectedError(
                    details={"device_id": self.output_device_id, "error": str(e)},
                )
                self.console.print(f"[red]✗[/red] {error.message}")
                self.console.print(f"[dim]💡 {error.suggestion}[/dim]")
            else:
                self.console.print(f"[red]Error:[/red] {e}")
            return False
        except (OSError, RuntimeError) as e:
            logger.exception("Playback error")
            self.console.print(f"[red]Error:[/red] {e}")
            return False
        else:
            self.console.print(
                f"[green]▶[/green] Playing: [bold]{audio_file.name}[/bold]",
            )
            return True

    def stop_audio(self) -> None:
        """Stop any currently playing audio."""
        try:
            sd.stop()
            logger.debug("Audio playback stopped")
        except (OSError, RuntimeError) as e:
            logger.exception("Error stopping audio")
            self.console.print(f"[red]Error stopping audio:[/red] {e}")

    def is_playing(self) -> bool:
        """Check if audio is currently playing.

        Returns:
            True if audio is currently playing, False otherwise.

        """
        return sd.get_stream().active if sd.get_stream() else False
