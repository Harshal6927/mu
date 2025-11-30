# Copyright (c) 2025. All rights reserved.
"""Custom hotkey management for MUC Soundboard."""

from typing import TYPE_CHECKING, ClassVar

from src.logging_config import get_logger

if TYPE_CHECKING:
    from .profile_manager import ProfileManager

logger = get_logger(__name__)


class HotkeyManager:
    """Manages custom hotkey bindings."""

    # Valid modifier keys
    MODIFIERS: ClassVar[set[str]] = {"ctrl", "alt", "shift", "cmd", "meta"}

    # Shorthand to pynput format
    KEY_ALIASES: ClassVar[dict[str, str]] = {
        "f1": "<f1>",
        "f2": "<f2>",
        "f3": "<f3>",
        "f4": "<f4>",
        "f5": "<f5>",
        "f6": "<f6>",
        "f7": "<f7>",
        "f8": "<f8>",
        "f9": "<f9>",
        "f10": "<f10>",
        "f11": "<f11>",
        "f12": "<f12>",
        "space": "<space>",
        "esc": "<esc>",
        "tab": "<tab>",
        "enter": "<enter>",
        "backspace": "<backspace>",
        "delete": "<delete>",
        "home": "<home>",
        "end": "<end>",
        "pageup": "<page_up>",
        "pagedown": "<page_down>",
        "up": "<up>",
        "down": "<down>",
        "left": "<left>",
        "right": "<right>",
        "insert": "<insert>",
        "numpad0": "<num_0>",
        "numpad1": "<num_1>",
        "numpad2": "<num_2>",
        "numpad3": "<num_3>",
        "numpad4": "<num_4>",
        "numpad5": "<num_5>",
        "numpad6": "<num_6>",
        "numpad7": "<num_7>",
        "numpad8": "<num_8>",
        "numpad9": "<num_9>",
    }

    def __init__(self, profile_manager: "ProfileManager | None" = None) -> None:
        """Initialize HotkeyManager.

        Args:
            profile_manager: ProfileManager instance (creates new if None)

        """
        if profile_manager is None:
            from .profile_manager import ProfileManager

            profile_manager = ProfileManager()
        self.profile_manager = profile_manager
        self.bindings: dict[str, str] = {}
        self._load_bindings()

    def _load_bindings(self) -> None:
        """Load bindings from profile."""
        profile = self.profile_manager.get_active_profile()
        self.bindings = profile.hotkeys.copy() if profile else {}
        logger.debug(f"Loaded {len(self.bindings)} custom hotkey bindings")

    def _save_bindings(self) -> None:
        """Save bindings to profile."""
        profile = self.profile_manager.get_active_profile()
        if profile:
            profile.hotkeys = self.bindings.copy()
            self.profile_manager.save_profile(profile)
        logger.debug("Saved hotkey bindings to profile")

    def normalize_hotkey(self, hotkey: str) -> str | None:
        """Normalize hotkey string to pynput format.

        Examples:
            "f1" -> "<f1>"
            "ctrl+a" -> "<ctrl>+a"
            "<ctrl>+<shift>+1" -> "<ctrl>+<shift>+1"

        Args:
            hotkey: Hotkey string in various formats

        Returns:
            Normalized hotkey string, or None if invalid format

        """
        hotkey = hotkey.lower().strip()

        # Check alias
        if hotkey in self.KEY_ALIASES:
            return self.KEY_ALIASES[hotkey]

        # Already in correct format (single key with angle brackets)
        if hotkey.startswith("<") and hotkey.endswith(">") and "+" not in hotkey:
            return hotkey

        # Parse modifier+key format
        # Handle both "ctrl+a" and "<ctrl>+a" formats
        parts = []
        for raw_part in hotkey.split("+"):
            cleaned = raw_part.strip().strip("<>")
            if cleaned:
                parts.append(cleaned)

        if not parts:
            return None

        normalized_parts = []
        for part in parts:
            if part in self.MODIFIERS:
                normalized_parts.append(f"<{part}>")
            elif part in self.KEY_ALIASES:
                normalized_parts.append(self.KEY_ALIASES[part])
            elif len(part) == 1 or part.isdigit():  # Single char or numeric string
                normalized_parts.append(part)
            else:
                # Assume it's a special key
                normalized_parts.append(f"<{part}>")

        return "+".join(normalized_parts)

    def bind(self, hotkey: str, sound_name: str) -> bool:
        """Bind a hotkey to a sound.

        Args:
            hotkey: Hotkey string (will be normalized)
            sound_name: Name of the sound to bind

        Returns:
            True if binding was successful

        """
        normalized = self.normalize_hotkey(hotkey)
        if not normalized:
            logger.warning(f"Invalid hotkey format: {hotkey}")
            return False

        self.bindings[normalized] = sound_name
        self._save_bindings()
        logger.info(f"Bound {normalized} -> {sound_name}")
        return True

    def unbind(self, hotkey: str) -> bool:
        """Unbind a hotkey.

        Args:
            hotkey: Hotkey string to unbind

        Returns:
            True if was bound and is now unbound

        """
        normalized = self.normalize_hotkey(hotkey)
        if not normalized:
            return False

        if normalized in self.bindings:
            del self.bindings[normalized]
            self._save_bindings()
            logger.info(f"Unbound {normalized}")
            return True
        return False

    def unbind_sound(self, sound_name: str) -> int:
        """Unbind all hotkeys for a sound.

        Args:
            sound_name: Name of the sound

        Returns:
            Number of hotkeys unbound

        """
        to_remove = [k for k, v in self.bindings.items() if v == sound_name]
        for key in to_remove:
            del self.bindings[key]
        if to_remove:
            self._save_bindings()
            logger.info(f"Unbound {len(to_remove)} hotkey(s) from {sound_name}")
        return len(to_remove)

    def get_binding(self, hotkey: str) -> str | None:
        """Get the sound bound to a hotkey.

        Args:
            hotkey: Hotkey string

        Returns:
            Sound name if bound, None otherwise

        """
        normalized = self.normalize_hotkey(hotkey)
        if not normalized:
            return None
        return self.bindings.get(normalized)

    def get_all_bindings(self) -> dict[str, str]:
        """Get all hotkey bindings.

        Returns:
            Copy of all bindings dictionary

        """
        return self.bindings.copy()

    def clear_all(self) -> int:
        """Clear all custom hotkey bindings.

        Returns:
            Number of bindings cleared

        """
        count = len(self.bindings)
        self.bindings.clear()
        self._save_bindings()
        logger.info(f"Cleared {count} hotkey binding(s)")
        return count

    def get_hotkeys_for_sound(self, sound_name: str) -> list[str]:
        """Get all hotkeys bound to a specific sound.

        Args:
            sound_name: Name of the sound

        Returns:
            List of hotkey strings

        """
        return [k for k, v in self.bindings.items() if v == sound_name]

    def is_valid_hotkey(self, hotkey: str) -> bool:
        """Check if a hotkey string is valid.

        Args:
            hotkey: Hotkey string to validate

        Returns:
            True if hotkey can be normalized

        """
        return self.normalize_hotkey(hotkey) is not None
