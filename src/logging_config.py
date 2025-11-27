# Copyright (c) 2025. All rights reserved.
"""Logging configuration for MUC Soundboard."""

import sys
from pathlib import Path

from loguru import logger

# Remove default handler
logger.remove()

# Default log directory
LOG_DIR = Path.home() / ".muc" / "logs"
LOG_FILE = LOG_DIR / "muc.log"

# Track if logging has been initialized
_initialized = False


def setup_logging(*, debug: bool = False, log_to_file: bool = True) -> None:
    """Configure logging for the application.

    Args:
        debug: Enable debug-level logging to console
        log_to_file: Enable logging to file

    """
    global _initialized  # noqa: PLW0603

    # Prevent re-initialization
    if _initialized:
        return

    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Console handler - INFO level by default, DEBUG if --debug flag
    console_level = "DEBUG" if debug else "INFO"
    console_format = (
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
        if debug
        else "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=console_format,
        level=console_level,
        colorize=True,
        filter=lambda record: record["level"].name != "SUCCESS" or debug,
    )

    # File handler - always DEBUG level for comprehensive logs
    if log_to_file:
        logger.add(
            LOG_FILE,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            rotation="1 MB",
            retention="5 days",
            compression="zip",
            enqueue=True,  # Thread-safe
        )

    _initialized = True
    logger.debug("Logging initialized")


def get_logger(name: str):  # noqa: ANN201
    """Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    """
    return logger.bind(name=name)


def init_logging(*, debug: bool = False) -> None:
    """Initialize logging (call once at startup).

    Args:
        debug: Enable debug-level logging to console

    """
    setup_logging(debug=debug)


def reset_logging() -> None:
    """Reset logging state (mainly for testing)."""
    global _initialized  # noqa: PLW0603
    logger.remove()
    _initialized = False
