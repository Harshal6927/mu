# MUC Soundboard - AI Coding Guidelines

## Project Overview

MUC is a Python CLI soundboard that routes audio through virtual microphones for gaming (CS, Battlefield, COD). It uses VB-Cable for audio routing and Rich-click for CLI output.

## BEHAVIORAL REQUIREMENTS (READ FIRST)

### Core Principles

1. **Verify Before Acting** - Never assume; always confirm understanding
2. **Research Before Implementing** - Search codebase and docs first
3. **Follow Existing Patterns** - Match the style of surrounding code
4. **Ask When Uncertain** - Questions are better than wrong assumptions

### When Uncertain

- ❌ **DO NOT** proceed with assumptions
- ❌ **DO NOT** invent new patterns when existing ones exist
- ✅ **DO** use Context7 for library documentation
- ✅ **DO** use Sequential Thinking for complex analysis
- ✅ **DO** ask clarifying questions
- ✅ **DO** search the codebase first

## Architecture

```
CLI (cli.py) → Soundboard → AudioManager → VB-Cable → Game
                  ↓
         MetadataManager (tags, favorites, volumes)
         HotkeyManager (custom key bindings)
         ProfileManager (game-specific configs)
```

**Key components:**
- `cli.py` - Entry point, all commands use `rich-click` decorators
- `soundboard.py` - Core orchestrator: scans sounds, manages hotkeys, coordinates playback
- `audio_manager.py` - Device handling, LRU caching, playback with numpy/sounddevice
- `config.py` - Legacy config, `profile_manager.py` - Modern multi-profile system
- `exceptions.py` - Hierarchical error codes (1xx config, 2xx device, 3xx file, 4xx hotkey)

## Development Workflow

```bash
# Run tests (uses pytest with mocks - no audio hardware needed)
make test
# or: uv run pytest tests/ -q

# Run with coverage
make coverage

# Lint with pre-commit (ruff)
make lint

# Run the app
uv run muc --help
```

## Code Patterns

### Imports - Use `src.` prefix
```python
from src.soundboard import Soundboard
from src.exceptions import MUCError, DeviceNotFoundError
```

### CLI commands follow this pattern:
```python
@cli.command()
@click.argument("sound_name")
@click.option("--flag", is_flag=True, help="Description")
def command_name(sound_name: str, flag: bool) -> None:
    """Docstring shown in help."""
    soundboard, audio_manager = get_soundboard()  # Standard initialization
    # ... implementation
```

### Error handling - Use custom exceptions from `exceptions.py`:
```python
from src.exceptions import AudioFileCorruptedError, DeviceNotFoundError

# Raise with structured info
raise DeviceNotFoundError(
    message="Device ID 99 not found",
    suggestion="Run 'muc devices' to see available devices",
    details={"device_id": 99}
)
```

### Testing - All tests mock audio hardware:
```python
# Use fixtures from conftest.py
def test_feature(
    mock_audio_manager: MagicMock,  # Mocked AudioManager
    mock_sounddevice: MagicMock,     # Mocked sd module
    temp_sounds_dir: Path,           # Temp dir with dummy audio files
    mock_audio_validation: MagicMock # Bypasses file validation
) -> None:
```

## Key Conventions

1. **Type hints everywhere** - All functions have return types
2. **Docstrings** - Google style with Args/Returns sections
3. **Console output** - Use Rich markup: `[green]✓[/green]`, `[red]✗[/red]`, `[yellow]⚠[/yellow]`
4. **Config storage** - `~/.muc/` directory (profiles, metadata, playlists)
5. **Audio formats** - WAV, MP3, OGG, FLAC, M4A (see `validators.SUPPORTED_FORMATS`)
6. **Line length** - 120 chars (configured in pyproject.toml)

## File Structure for New Features

- New command → Add to `cli.py`, follow existing command patterns
- New manager class → Create `src/<feature>.py`, add tests in `tests/unit/test_<feature>.py`
- New exception → Add to `exceptions.py` hierarchy with appropriate error code range

## Testing Notes

- Tests run without real audio devices (all mocked)
- Use `mock_audio_validation` fixture to bypass audio file checks
- Coverage threshold: 65% (enforced in pyproject.toml)
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`
