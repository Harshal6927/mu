# MUC Soundboard AI Instructions

## 🏗 Architecture & Data Flow

- **Core Components**:
  - `CLI` (`src/cli.py`): Entry point using `rich-click`. Orchestrates `Soundboard` and `AudioManager`.
  - `Config` (`src/config.py`): Persists state (device ID, volume) to `~/.muc/config.json`.
  - `Soundboard` (`src/soundboard.py`): Manages sound library (scanning `sounds/`) and `pynput` hotkey bindings.
  - `AudioManager` (`src/audio_manager.py`): Low-level audio I/O via `sounddevice` and `soundfile`.

- **Audio Routing Strategy**:
  - The app outputs audio to a **Virtual Audio Cable** (e.g., VB-Cable).
  - **Critical**: The app must output to the "Input" side of the virtual cable (e.g., `CABLE Input`).
  - Games/Apps read from the "Output" side (e.g., `CABLE Output`) as a microphone.
  - `AudioManager.find_virtual_cable()` auto-detects devices with keywords: "cable", "virtual", "vb-audio".

- **Data Flow**:
  `CLI Command/Hotkey` -> `Soundboard` -> `AudioManager.play_audio()` -> `soundfile.read()` -> `numpy` processing (volume/channels) -> `sounddevice.play()` -> `Virtual Device`.

## 🛠 Developer Workflows

- **Dependency Management**: Use `uv` for package management.
  - Install: `uv add muc` or `uv sync`
  - Run: `uv run muc`
- **Linting**: Run `make lint` to execute pre-commit hooks (ruff, etc.).
- **Testing Audio**:
  - Use `muc devices` to list IDs.
  - Use `muc play [name]` to test playback without hotkeys.
  - `AudioManager.play_audio(..., blocking=True)` is used for sequential playback (e.g., `muc auto`).

## 🧩 Patterns & Conventions

- **UI/UX**:
  - **ALWAYS** use `rich.console.Console` for output. Never use `print()`.
  - Use `rich.table.Table` for listing data (devices, sounds).
  - Use `rich.panel.Panel` for welcome messages/headers.
  - Style errors with `[red]✗[/red]` and successes with `[green]✓[/green]`.

- **Audio Handling**:
  - **Channel Mapping**: `AudioManager` automatically upmixes mono files to match the output device's channel count using `numpy.tile`.
  - **Volume**: Applied as a scalar multiplication on the numpy array *before* playback.
  - **Non-blocking by default**: `play_audio` is fire-and-forget unless `blocking=True` is passed.

- **Configuration**:
  - Config is auto-loaded on instantiation of `Config()`.
  - `Config.save()` must be called explicitly after modifying settings.
  - Paths are handled with `pathlib.Path`.

- **Error Handling**:
  - Catch `OSError` and `RuntimeError` from `sounddevice`/`pynput`.
  - Display user-friendly messages via `console.print` instead of letting the app crash.
  - Example:
    ```python
    try:
        sd.play(data, samplerate)
    except (OSError, RuntimeError) as e:
        self.console.print(f"[red]Error:[/red] {e}")
    ```

## 🔑 Key Integration Points

- **Hotkeys**:
  - Uses `pynput.keyboard.GlobalHotKeys`.
  - The listener runs in a daemon thread, but the CLI command (`listen`) must keep the main thread alive (often with a `keyboard.Listener` blocking on `join()`).
- **File Discovery**:
  - Recursively scans `sounds/` for extensions: `.wav`, `.mp3`, `.ogg`, `.flac`, `.m4a`.
  - Uses `pathlib.Path.rglob("*")`.
